import re
from typing import Any


_PROMPT_TRANSLATION_TABLE = str.maketrans(
    {
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2032": "'",
        "\u2033": '"',
    }
)

_FINAL_PROMPT_PATTERNS = (
    r"\(\s*f\s*\)\s*final optimized prompt\s*[:\-]?\s*(.+)$",
    r"\(\s*f\s*\)\s*final prompt\s*[:\-]?\s*(.+)$",
    r"final optimized prompt\s*[:\-]?\s*(.+)$",
    r"final prompt\s*[:\-]?\s*(.+)$",
)


def normalize_prompt_text(raw_text: Any) -> str:
    text = str(raw_text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_PROMPT_TRANSLATION_TABLE)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return " ".join(text.split())


def extract_final_optimized_prompt(raw_text: Any) -> str:
    text = str(raw_text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern in _FINAL_PROMPT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = match.group(1).strip(" \t:-\n")
            if candidate:
                return candidate
    return ""


def build_prompt_variants(raw_text: Any) -> list[dict]:
    prompt_text = normalize_prompt_text(raw_text)
    if not prompt_text:
        return []

    variants = [{
        "name": "full_prompt",
        "label": "tam icerik",
        "prompt": prompt_text,
    }]

    sanitized_text = sanitize_sensitive_prompt_text(raw_text)
    if sanitized_text and sanitized_text != prompt_text:
        variants.append({
            "name": "full_prompt_sensitive_cleaned",
            "label": "tam icerik (hassas temizlenmis)",
            "prompt": sanitized_text,
        })

    final_optimized_prompt = normalize_prompt_text(extract_final_optimized_prompt(raw_text))
    if final_optimized_prompt and all(final_optimized_prompt != item["prompt"] for item in variants):
        variants.append({
            "name": "final_optimized_prompt",
            "label": "yalniz Final optimized prompt",
            "prompt": final_optimized_prompt,
        })

    return variants


def sanitize_sensitive_prompt_text(raw_text: Any) -> str:
    text = normalize_prompt_text(raw_text)
    if not text:
        return ""

    # Watermark satirlari ve icerdigi handle/metin, PixVerse tarafinda
    # "sensitive information" hatasina sebep olabildigi icin temizlenir.
    text = re.sub(
        r"\bthere is a watermark[^.?!]*[.?!]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bwatermark[^.?!]*reads[^.?!]*[.?!]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "contact address", text)
    text = re.sub(r"(?<!\w)@[\w.]{2,}", "creator tag", text)
    text = re.sub(r"https?://\S+|www\.\S+", "source link", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:\+?\d[\d().\-\s]{7,}\d)\b", "contact number", text)

    return normalize_prompt_text(text)


def is_sensitive_info_error_message(text: Any) -> bool:
    haystack = str(text or "").casefold()
    return (
        "contains sensitive information" in haystack
        or "sensitive information" in haystack
        or "please re-enter" in haystack
    )


def first_meaningful_line(text: Any, max_length: int = 180) -> str:
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if line in {"{", "}", "{}", "[]", "[", "]"}:
            continue
        return line[:max_length]
    return ""


def _extract_from_error_value(value: Any, max_length: int = 180) -> str:
    if isinstance(value, dict):
        for key in ("message", "detail", "msg", "error", "reason", "description"):
            detail = _extract_from_error_value(value.get(key), max_length=max_length)
            if detail:
                return detail
        for nested_value in value.values():
            detail = _extract_from_error_value(nested_value, max_length=max_length)
            if detail:
                return detail
        return ""

    if isinstance(value, (list, tuple, set)):
        for item in value:
            detail = _extract_from_error_value(item, max_length=max_length)
            if detail:
                return detail
        return ""

    return first_meaningful_line(value, max_length=max_length)


def extract_json_error_text(data: Any, max_length: int = 180) -> str:
    if not isinstance(data, dict):
        return ""

    for key in ("error", "message", "detail", "msg", "reason", "description"):
        detail = _extract_from_error_value(data.get(key), max_length=max_length)
        if detail:
            return detail

    for value in data.values():
        detail = _extract_from_error_value(value, max_length=max_length)
        if detail:
            return detail

    return ""
