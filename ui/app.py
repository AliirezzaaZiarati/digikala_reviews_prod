import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

# Direct image URL pattern; only the numeric status code changes
ERROR_IMAGE_URL = "https://httpstatusdogs.com/img/picture-perfect/{code}.jpg"

st.set_page_config(page_title="Digikala Review Analyzer", page_icon="✨", layout="centered")

# ---------- Design ----------
# Abstract line art for the background (an SVG inside a CSS data URI).
BG_LINES = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='1440' height='900' viewBox='0 0 1440 900' fill='none'>"
    "<path d='M-60 720 C 220 520, 420 860, 700 620 S 1180 340, 1500 520' stroke='rgb(124,92,255)' stroke-opacity='.22' stroke-width='1.6'/>"
    "<path d='M-60 780 C 260 600, 460 900, 760 690 S 1220 420, 1500 600' stroke='rgb(0,184,217)' stroke-opacity='.20' stroke-width='1.4'/>"
    "<path d='M-60 140 C 240 20, 520 260, 820 120 S 1240 -40, 1500 160' stroke='rgb(255,107,157)' stroke-opacity='.20' stroke-width='1.4'/>"
    "<circle cx='1180' cy='220' r='170' stroke='rgb(124,92,255)' stroke-opacity='.14'/>"
    "<circle cx='1180' cy='220' r='120' stroke='rgb(0,184,217)' stroke-opacity='.14'/>"
    "<circle cx='160' cy='760' r='140' stroke='rgb(255,107,157)' stroke-opacity='.14'/>"
    "</svg>"
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&family=Vazirmatn:wght@400;500;700;800&display=swap');

.stApp {
  font-family: 'Vazirmatn', 'Segoe UI', system-ui, sans-serif;
  background:
    url("__BG__") center / cover no-repeat,
    radial-gradient(900px 600px at 8% 6%, rgba(124,92,255,.16), transparent 60%),
    radial-gradient(800px 560px at 96% 12%, rgba(0,184,217,.15), transparent 60%),
    radial-gradient(900px 640px at 80% 98%, rgba(255,107,157,.15), transparent 60%),
    linear-gradient(135deg, #F8F7FF 0%, #F2F9FF 50%, #FFF6FA 100%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 760px; padding-top: 2.2rem; }

.material-symbols-rounded {
  font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
  line-height: 1; display: inline-block; vertical-align: middle;
  font-feature-settings: 'liga'; -webkit-font-feature-settings: 'liga';
}

/* Hero */
.hero { text-align: center; margin-bottom: 1.5rem; }
.hero .badge {
  display: inline-flex; align-items: center; gap: .4rem; padding: .35rem .85rem;
  border-radius: 999px; background: rgba(124,92,255,.10); color: #6C4DFF;
  font-weight: 600; font-size: .82rem;
}
.hero h1 {
  font-size: 2.5rem; font-weight: 800; margin: .8rem 0 .3rem; line-height: 1.25;
  background: linear-gradient(90deg, #6C4DFF, #00A6D6 55%, #FF5C93);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: #5B6475; margin: 0; }

/* Input card (st.container with border) */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,.72); backdrop-filter: blur(12px);
  border: 1px solid rgba(124,92,255,.16); border-radius: 22px;
  box-shadow: 0 12px 34px rgba(80,70,160,.09);
}
.stTextArea textarea {
  border-radius: 14px; background: rgba(255,255,255,.92); font-family: inherit;
  direction: rtl; text-align: right; font-size: 1.02rem;
}
div[data-baseweb="select"] > div { border-radius: 12px; background: rgba(255,255,255,.92); }

/* Button */
.stButton > button {
  border: 0; border-radius: 14px; padding: .65rem 1rem; font-weight: 700; font-family: inherit;
  background: linear-gradient(90deg, #6C4DFF, #00A6D6); color: #fff;
  box-shadow: 0 8px 20px rgba(108,77,255,.28); transition: transform .15s, box-shadow .15s;
}
.stButton > button p { color: #fff; }
.stButton > button:hover {
  transform: translateY(-1px); box-shadow: 0 12px 26px rgba(108,77,255,.36); color: #fff;
}

/* Results */
.res-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.2rem; }
@media (max-width: 640px) { .res-grid { grid-template-columns: 1fr; } }
.card {
  background: rgba(255,255,255,.78); backdrop-filter: blur(10px);
  border: 1px solid rgba(124,92,255,.14); border-radius: 20px; padding: 1.2rem 1.3rem;
  box-shadow: 0 10px 30px rgba(80,70,160,.08);
}
.card-head { display: flex; align-items: center; gap: .5rem; color: #5B6475; font-weight: 600; font-size: .9rem; }
.card-head .material-symbols-rounded { font-size: 1.3rem; color: #6C4DFF; }
.verdict {
  display: inline-flex; align-items: center; gap: .45rem; margin: .7rem 0 1rem;
  padding: .4rem .95rem; border-radius: 999px; font-weight: 700; font-size: 1.05rem;
}
.row { margin: .6rem 0; }
.row-top { display: flex; justify-content: space-between; font-size: .85rem; color: #44506A; margin-bottom: .25rem; }
.track { height: 9px; border-radius: 999px; background: rgba(100,110,150,.12); overflow: hidden; }
.fill { height: 100%; border-radius: 999px; }
.meta { display: flex; gap: .6rem; flex-wrap: wrap; justify-content: center; margin-top: 1rem; }
.chip {
  display: inline-flex; align-items: center; gap: .35rem; padding: .3rem .8rem; border-radius: 999px;
  background: rgba(255,255,255,.75); border: 1px solid rgba(124,92,255,.14);
  color: #5B6475; font-size: .8rem; font-weight: 500;
}
.chip .material-symbols-rounded { font-size: 1rem; color: #6C4DFF; }
""".replace("__BG__", BG_LINES)

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.markdown(
    '<div class="hero">'
    '<span class="badge"><span class="material-symbols-rounded">auto_awesome</span>Persian review intelligence</span>'
    "<h1>Digikala Review Analyzer</h1>"
    "<p>Recommendation and rating band from the review text alone</p>"
    "</div>",
    unsafe_allow_html=True,
)

# label -> (display name, color, icon)
LABEL_STYLE = {
    "recommended": ("Recommended", "#12B76A", "thumb_up"),
    "not_recommended": ("Not recommended", "#F04438", "thumb_down"),
    "no_idea": ("No idea", "#F79009", "help"),
    "low": ("Low", "#F04438", "sentiment_dissatisfied"),
    "medium": ("Medium", "#F79009", "sentiment_neutral"),
    "high": ("High", "#12B76A", "sentiment_satisfied"),
}
HEADS = (
    ("recommendation", "Recommendation", "thumbs_up_down"),
    ("rating_band", "Rating band", "stars"),
)


def prob_rows(probs: dict) -> str:
    rows = []
    for label, p in probs.items():
        name, color, _ = LABEL_STYLE.get(label, (label, "#6C4DFF", "label"))
        pct = p * 100
        rows.append(
            '<div class="row"><div class="row-top">'
            f"<span>{name}</span><span>{pct:.1f}%</span></div>"
            '<div class="track">'
            f'<div class="fill" style="width:{pct:.1f}%;background:linear-gradient(90deg,{color}99,{color})"></div>'
            "</div></div>"
        )
    return "".join(rows)


def result_card(title: str, icon: str, head: dict) -> str:
    name, color, label_icon = LABEL_STYLE.get(head["label"], (head["label"], "#6C4DFF", "label"))
    return (
        '<div class="card">'
        f'<div class="card-head"><span class="material-symbols-rounded">{icon}</span>{title}</div>'
        f'<div class="verdict" style="background:{color}1F;color:{color}">'
        f'<span class="material-symbols-rounded">{label_icon}</span>{name}</div>'
        f"{prob_rows(head['probabilities'])}"
        "</div>"
    )


def show_error(resp: requests.Response):
    st.error(f"Error {resp.status_code}: {resp.text}")
    st.image(ERROR_IMAGE_URL.format(code=resp.status_code), width=360)


# ---------- App ----------
try:
    models = requests.get(f"{API_URL}/models", timeout=5).json()
except requests.RequestException:
    st.error("API is not reachable. Is the FastAPI service running?")
    st.stop()

names = {m["name"]: m["id"] for m in models}

with st.container(border=True):
    choice = st.selectbox("Model", list(names))
    text = st.text_area("Review text", height=150, placeholder="نظر خود را درباره‌ی محصول اینجا بنویسید…")
    clicked = st.button("Analyze review", type="primary", icon=":material/auto_awesome:", use_container_width=True)

if clicked:
    if not text.strip():
        st.warning("Please enter a review text first.")
        st.stop()
    with st.spinner("Analyzing..."):
        resp = requests.post(
            f"{API_URL}/predict",
            json={"text": text, "model_id": names[choice]},
            timeout=120,
        )
    if resp.status_code != 200:
        show_error(resp)
    else:
        data = resp.json()
        cards = "".join(result_card(title, icon, data[key]) for key, title, icon in HEADS)
        meta = (
            '<div class="meta">'
            f'<span class="chip"><span class="material-symbols-rounded">memory</span>{data["model_name"]}</span>'
            f'<span class="chip"><span class="material-symbols-rounded">bolt</span>{data["latency_ms"]} ms</span>'
            "</div>"
        )
        st.markdown(f'<div class="res-grid">{cards}</div>{meta}', unsafe_allow_html=True)