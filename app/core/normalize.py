"""
normalize.py - production Persian review-text normalizer.

Pure Python (re only). Mirrors the DuckDB pipeline from the notebooks,
rule by rule and in the same order, plus Unicode normalization,
optional Persian suffix joining, stray ZWNJ cleanup, and final emoji spacing.

    from normalize import normalize_text

    normalize_text("كيفيت ممتاز😍")
    # -> "کیفیت ممتاز 😍"

    normalize_text("کتاب ها")
    # -> "کتاب ها"

    normalize_text("کتاب ها", join_suffixes=True)
    # -> "کتاب‌ها"

Returns None for None / empty / whitespace-only / URL-only input.
"""
from __future__ import annotations

import re
import sys
import unicodedata

NORMALIZER_VERSION = "2.1"
ZWNJ = "\u200c"


# ---------------------------------------------------------------------------
# Character tables
# ---------------------------------------------------------------------------

_LETTER_TABLE = str.maketrans(
    "\u064a\u0649\u0643",
    "\u06cc\u06cc\u06a9",
)  # ي ى ك -> ی ی ک

_HEH_TABLE = str.maketrans(
    "\u06be\u06c1",
    "\u0647\u0647",
)  # ھ ہ -> ه

_EXTRA_LETTER_TABLE = str.maketrans({
    "\u0623": "\u0627",  # أ -> ا
    "\u0625": "\u0627",  # إ -> ا
    "\u0671": "\u0627",  # ٱ -> ا
    "\u0629": "\u0647",  # ة -> ه
    "\u06c0": "\u0647",  # ۀ -> ه
    "\u06d2": "\u06cc",  # ے -> ی
    "\u06aa": "\u06a9",  # ڪ -> ک
})

_DIGIT_TABLE = str.maketrans(
    "".join(chr(0x0660 + i) for i in range(10)) + "0123456789",
    "".join(chr(0x06F0 + i) for i in range(10)) * 2,
)


# ---------------------------------------------------------------------------
# Symbol sets
# ---------------------------------------------------------------------------

P_CHARS = ".!\u061f\u060c\u061b:"

EMOJI_CLASS = (
    "\U0001F000-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\u2300-\u23FF"
    "\uFE0F"
)

QUOTE_CHARS = (
    "\u00ab\u00bb\u201c\u201d\u201e\u201f"
    "\u2039\u203a\u2033"
)

DASH_CHARS = (
    "_\u2014\u2013\u2010\u2011\u2012\u2015"
    "\u2212\ufe58\ufe63\uff0d"
)

PERCENT_CHARS = "\u066a\uff05\ufe6a"

SYMBOL_TABLE = {}

SYMBOL_TABLE.update({
    ord(c): '"'
    for c in QUOTE_CHARS
})

SYMBOL_TABLE.update({
    ord(c): "-"
    for c in DASH_CHARS
})

SYMBOL_TABLE.update({
    ord(c): "%"
    for c in PERCENT_CHARS
})

SYMBOL_TABLE[ord("{")] = "["
SYMBOL_TABLE[ord("}")] = "]"
SYMBOL_TABLE[ord("?")] = "\u061f"
SYMBOL_TABLE[ord(";")] = "\u061b"
SYMBOL_TABLE[ord("\u2026")] = "..."

LAT_DIGIT = "0-9A-Za-z\u06f0-\u06f9"


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_HTML_ENTITIES = (
    ("&nbsp;", " "),
    ("&amp;", "&"),
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&zwnj;", ZWNJ),
)

_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")

_ESCAPED_ZWNJ_RE = re.compile(
    r"\\u200c",
    re.IGNORECASE,
)

_INVISIBLE_RE = re.compile(
    r"[\u200B\u200D\u200E\u200F\u202A-\u202E"
    r"\u2060-\u2064\u2066-\u2069\uFEFF\u00AD]"
)

_SPACE_CTRL_RE = re.compile(
    r"[\u0001-\u001F\u007F-\u009F\u00A0\u1680"
    r"\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]"
)

_URL_RE = re.compile(
    r"(?:https?://|www\.)"
    r"[A-Za-z0-9._~:/?#@!$&*+,;=%()\[\]-]+",
    re.IGNORECASE,
)

_DIACRITICS_RE = re.compile(
    r"[\u064B-\u065F\u0670\u0640]"
)

_ANGLE_PAIR_RE = re.compile(
    r"<(\S(?:[^<>]*\S)?)>"
)

_THOUSANDS_RE = re.compile(
    r"(?<![\d,\u066c])"
    r"\d{1,3}(?:[,\u066c]\d{3})+"
    r"(?!\d)"
)

_COMMA_RE = re.compile(
    "(?<![" + LAT_DIGIT + "]),|,(?![" + LAT_DIGIT + "])"
)

_REPEAT_RE = re.compile(
    r"([^\d\s\u200c.()])\1{2,}"
)

_DOTS_RE = re.compile(
    r"\.{2,}"
)

_RUN_RE = re.compile(
    "( *)([" + P_CHARS + EMOJI_CLASS + "]["
    + P_CHARS + EMOJI_CLASS + "()]*)"
)

_SYMBOL_RE = re.compile(
    "[" + P_CHARS + EMOJI_CLASS + "]"
)

_STRUCT_RE = re.compile(
    r'(\s*)("+|\(+|\)+|\[+|\]+)(\s*)'
)

_PAREN_OPEN = "\ue000"
_PAREN_CLOSE = "\ue001"


# ZWNJ is now considered a word boundary-aware character
_SINGLE_LETTER_RE = re.compile(
    r"(?<![\w\u200c])"
    r"[\u0621-\u064A\u066E-\u06D3\u06FA-\u06FC]"
    r"(?![\w\u200c])"
)


_MULTI_SPACE_RE = re.compile(
    r" {2,}"
)

_MULTI_ZWNJ_RE = re.compile(
    r"\u200c{2,}"
)

_TRIM_RE = re.compile(
    r"^[ \u200c]+|[ \u200c]+$"
)


# ---------------------------------------------------------------------------
# Emoji spacing
# ---------------------------------------------------------------------------

_EMOJI = "[" + EMOJI_CLASS + "]"

_WORD = r"[\w\u200c]"

_EMOJI_AFTER_WORD_RE = re.compile(
    rf"(?<={_WORD})(?!\uFE0F){_EMOJI}"
)

_EMOJI_BEFORE_WORD_RE = re.compile(
    rf"{_EMOJI}(?={_WORD})"
)


# ---------------------------------------------------------------------------
# Persian / Latin detection
# ---------------------------------------------------------------------------

_PERSIAN_LETTER_RE = re.compile(
    r"[\u0621-\u063A\u0641-\u064A\u066E-\u06D3"
    r"\uFB50-\uFDFF\uFE70-\uFEFF]"
)

_LATIN_LETTER_RE = re.compile(
    r"[A-Za-z]"
)


# ---------------------------------------------------------------------------
# ZWNJ cleanup
# ---------------------------------------------------------------------------

# ZWNJ is valid only when surrounded by word characters.
_STRAY_ZWNJ_RE = re.compile(
    r"(?<!\w)\u200c|\u200c(?!\w)"
)


# ---------------------------------------------------------------------------
# Optional Persian suffix / prefix joining
# ---------------------------------------------------------------------------

_FA_LETTER = (
    r"[\u0621-\u064A\u066E-\u06D3\u06FA-\u06FC]"
)

_PLURAL_RE = re.compile(
    rf"(?<={_FA_LETTER}) "
    rf"(هایی|های|ها)"
    rf"(?![\w\u200c])"
)

_MI_PREFIX_RE = re.compile(
    rf"(?<![\w\u200c])"
    rf"(ن?می) "
    rf"(?={_FA_LETTER})"
)


# ---------------------------------------------------------------------------
# Rules (each: str -> str)
# ---------------------------------------------------------------------------

def _html(s: str) -> str:
    for old, new in _HTML_ENTITIES:
        s = s.replace(old, new)

    return _HTML_TAG_RE.sub(" ", s)


def _unify_symbols(s: str) -> str:
    s = s.replace("<<", '"').replace(">>", '"')

    s = _ANGLE_PAIR_RE.sub(
        r'"\1"',
        s,
    )  # <text> -> "text"

    s = s.translate(SYMBOL_TABLE)

    s = _THOUSANDS_RE.sub(
        lambda m: (
            m.group(0)
            .replace(",", "")
            .replace("\u066c", "")
        ),
        s,
    )

    return _COMMA_RE.sub(
        "\u060c",
        s,
    )  # "," -> "،" (not between digits/Latin)


def _is_latin_or_digit(ch: str) -> bool:
    return bool(ch) and (
        (ch.isascii() and ch.isalnum())
        or "\u06f0" <= ch <= "\u06f9"
    )


def _glue_run(m: re.Match) -> str:
    s = m.string

    spaces, run = m.group(1), m.group(2)

    prev_ch = (
        s[m.start() - 1]
        if m.start() > 0
        else ""
    )

    next_ch = (
        s[m.end()]
        if m.end() < len(s)
        else ""
    )

    # 3.5, 12:30, a.com
    # A single "." or ":" between digits/Latin chars stays unchanged.
    if (
        run in (".", ":")
        and not spaces
        and _is_latin_or_digit(prev_ch)
        and _is_latin_or_digit(next_ch)
    ):
        return m.group(0)

    run = re.sub(
        r"\({3,}",
        "((",
        run,
    )

    run = re.sub(
        r"\){3,}",
        "))",
        run,
    )

    run = run.replace(
        "(",
        _PAREN_OPEN,
    ).replace(
        ")",
        _PAREN_CLOSE,
    )

    lead = (
        ""
        if (spaces and prev_ch.isalnum())
        else spaces
    )

    tail = (
        " "
        if next_ch.isalnum()
        else ""
    )

    return lead + run + tail


def _space_struct(m: re.Match) -> str:
    s = m.string

    token, after = m.group(2), m.group(3)

    if token[0] in "()" and len(token) >= 3:
        token = token[0]

    lead = (
        " "
        if m.start() > 0
        else ""
    )

    end = m.end()

    if end >= len(s):
        tail = ""

    elif after:
        tail = " "

    elif _SYMBOL_RE.match(s[end]):
        tail = ""

    else:
        tail = " "

    return lead + token + tail


def _space_symbols(s: str) -> str:
    s = _MULTI_SPACE_RE.sub(
        " ",
        s,
    )

    s = _RUN_RE.sub(
        _glue_run,
        s,
    )

    s = _STRUCT_RE.sub(
        _space_struct,
        s,
    )

    return s.replace(
        _PAREN_OPEN,
        "(",
    ).replace(
        _PAREN_CLOSE,
        ")",
    )


def _remove_single_letters(s: str) -> str:
    return _SINGLE_LETTER_RE.sub(
        lambda m: (
            m.group(0)
            if m.group(0) == "\u0648"
            else ""
        ),
        s,
    )


def _join_suffixes(s: str) -> str:
    # کتاب ها -> کتاب‌ها
    s = _PLURAL_RE.sub(
        ZWNJ + r"\1",
        s,
    )

    # نمی کنم -> نمی‌کنم
    return _MI_PREFIX_RE.sub(
        r"\1" + ZWNJ,
        s,
    )


def _emoji_spacing(s: str) -> str:
    s = _EMOJI_AFTER_WORD_RE.sub(
        r" \g<0>",
        s,
    )

    return _EMOJI_BEFORE_WORD_RE.sub(
        r"\g<0> ",
        s,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

# Order matters: do not reorder.
RULES = [
    ("NORM_unicode",          lambda s: unicodedata.normalize("NFKC", s)),
    ("NORM_html",            _html),
    ("NORM_escaped_zwnj",    lambda s: _ESCAPED_ZWNJ_RE.sub(ZWNJ, s)),
    ("NORM_invisible",       lambda s: _INVISIBLE_RE.sub("", s)),
    ("NORM_space_ctrl",      lambda s: _SPACE_CTRL_RE.sub(" ", s)),
    ("NORM_url",             lambda s: _URL_RE.sub(" ", s)),
    (
        "NORM_arabic_letters",
        lambda s: s.translate(_LETTER_TABLE).translate(_EXTRA_LETTER_TABLE),
    ),
    ("NORM_heh",             lambda s: s.translate(_HEH_TABLE)),
    ("NORM_diacritics",     lambda s: _DIACRITICS_RE.sub("", s)),
    ("NORM_digits",          lambda s: s.translate(_DIGIT_TABLE)),
    ("NORM_symbols_unify",   _unify_symbols),
    ("NORM_repeats",        lambda s: _REPEAT_RE.sub(r"\1\1", s)),
    ("NORM_dots",           lambda s: _DOTS_RE.sub("...", s)),
    ("NORM_symbol_spacing", _space_symbols),
    ("NORM_single_letters", _remove_single_letters),
    ("NORM_stray_zwnj",    lambda s: _STRAY_ZWNJ_RE.sub("", s)),
    (
        "NORM_spaces",
        lambda s: _MULTI_ZWNJ_RE.sub(
            ZWNJ,
            _MULTI_SPACE_RE.sub(" ", s),
        ),
    ),
    ("NORM_trim",           lambda s: _TRIM_RE.sub("", s)),
    ("NORM_join_suffixes",  _join_suffixes),
    ("NORM_emoji_spacing",  _emoji_spacing),
]


# ---------------------------------------------------------------------------
# Rule activation
# ---------------------------------------------------------------------------

def _active_rules(join_suffixes: bool):
    return [
        (rule_id, fn)
        for rule_id, fn in RULES
        if join_suffixes or rule_id != "NORM_join_suffixes"
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_text(
    text: str | None,
    *,
    join_suffixes: bool = False,
) -> str | None:
    """Normalize one review body. Returns None if nothing is left."""

    if text is None:
        return None

    if not isinstance(text, str):
        raise TypeError(
            f"expected str or None, got {type(text).__name__}"
        )

    for _, fn in _active_rules(join_suffixes):
        text = fn(text)

    return text or None


def normalize_batch(
    texts,
    *,
    join_suffixes: bool = False,
) -> list[str | None]:
    """Normalize a batch of review texts."""

    return [
        normalize_text(
            text,
            join_suffixes=join_suffixes,
        )
        for text in texts
    ]


def trace(
    text: str,
    *,
    join_suffixes: bool = False,
) -> list[tuple[str, str, str]]:
    """
    Return (rule_id, before, after) for every rule that changed the text.
    Useful for explanations and debugging.
    """

    steps = []

    for rule_id, fn in _active_rules(join_suffixes):
        new = fn(text)

        if new != text:
            steps.append(
                (rule_id, text, new)
            )

        text = new

    return steps


def is_latin_only(text: str | None) -> bool:
    """Flag only (no change): has Latin letters and no Persian letters."""

    return (
        bool(text)
        and bool(_LATIN_LETTER_RE.search(text))
        and not bool(_PERSIAN_LETTER_RE.search(text))
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(
            repr(
                normalize_text(arg)
            )
        )