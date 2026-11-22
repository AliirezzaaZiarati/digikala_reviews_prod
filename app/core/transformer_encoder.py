import json
import os

import torch
from torch import nn
from transformers import AutoConfig, AutoModel, AutoTokenizer

from app.core.base import BaseModel


class _TwoHeadClassifier(nn.Module):
    """Same layout as training: encoder + one Linear per head (dropout is off at inference)."""

    def __init__(self, encoder, head_sizes: dict[str, int]):
        super().__init__()
        self.encoder = encoder
        hidden = int(encoder.config.hidden_size)
        self.heads = nn.ModuleDict({h: nn.Linear(hidden, n) for h, n in head_sizes.items()})

    def forward(self, input_ids, attention_mask):
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        features = hidden[:, 0]  # the [CLS] position, as in training
        return {h: layer(features) for h, layer in self.heads.items()}


class TransformerEncoderModel(BaseModel):
    def load(self) -> None:
        run_dir = os.path.join(self.models_root, self.cfg["run_dir"])
        tok_dir = os.path.join(run_dir, "tokenizer")

        # 1) Tokenizer: the backend is read from the file saved at training time.
        with open(os.path.join(tok_dir, "tokenizer_backend.json"), encoding="utf-8") as f:
            info = json.load(f)
        self.backend = info["backend"]
        self.max_length = int(info["max_length"])
        if self.backend == "sentencepiece":
            import sentencepiece as spm  # lazy: only needed for this backend

            self.sp = spm.SentencePieceProcessor(model_file=os.path.join(tok_dir, "spm.model"))
            self.first_id = int(info["special_ids"]["first"])
            self.last_id = int(info["special_ids"]["last"])
        elif self.backend == "hf_fast":
            self.tokenizer = AutoTokenizer.from_pretrained(tok_dir, local_files_only=True)
        else:
            raise ValueError(f"unknown tokenizer backend: {self.backend}")

        # 2) Empty encoder skeleton from the saved config (the weights come from the .pt).
        with open(os.path.join(run_dir, "encoder_config.json"), encoding="utf-8") as f:
            enc_cfg = json.load(f)
        model_type = enc_cfg.pop("model_type")
        encoder = AutoModel.from_config(AutoConfig.for_model(model_type, **enc_cfg))
        if getattr(encoder, "pooler", None) is not None:
            encoder.pooler = None  # training dropped the pooler too

        # 3) Heads: YAML output name -> (head name in the checkpoint, labels).
        self.head_map = {}
        head_sizes = {}
        for out_name, head_cfg in self.cfg["heads"].items():
            labels = {int(k): v for k, v in head_cfg["labels"].items()}
            ckpt_head = head_cfg["checkpoint_head"]
            self.head_map[out_name] = (ckpt_head, labels)
            head_sizes[ckpt_head] = len(labels)

        # 4) Weights: strict=True so any mismatch fails loudly instead of predicting garbage.
        model = _TwoHeadClassifier(encoder, head_sizes)
        state = torch.load(os.path.join(run_dir, self.cfg["checkpoint"]), map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)

        want = self.cfg.get("device", "auto")
        self.device = "cuda" if (want == "auto" and torch.cuda.is_available()) else (want if want != "auto" else "cpu")
        self.model = model.to(self.device).eval()

    def _encode(self, text: str) -> list[int]:
        if self.backend == "sentencepiece":
            body = self.sp.encode(text)[: self.max_length - 2]
            return [self.first_id, *body, self.last_id]
        return self.tokenizer(text, truncation=True, max_length=self.max_length)["input_ids"]

    def predict(self, text: str) -> dict:
        input_ids = torch.tensor([self._encode(text)], device=self.device)
        attention_mask = torch.ones_like(input_ids)
        with torch.inference_mode():
            logits = self.model(input_ids, attention_mask)
        result = {}
        for out_name, (ckpt_head, labels) in self.head_map.items():
            probs = torch.softmax(logits[ckpt_head].float(), dim=-1)[0].tolist()
            by_label = {labels[i]: float(p) for i, p in enumerate(probs)}
            result[out_name] = {"label": max(by_label, key=by_label.get), "probabilities": by_label}
        return result