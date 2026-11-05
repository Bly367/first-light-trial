"""Comparison-only normalization (SPEC §3). Raw values are always kept and shown."""
import unicodedata
from decimal import Decimal, InvalidOperation

NO_OBSERVATION = {"", "unknown", "none"}


def _text(value):
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def normalize(value, value_type="text"):
    text = _text(value or "")
    if value_type == "int":
        try:
            return format(Decimal(text).normalize(), "f")
        except InvalidOperation:
            pass
    return text


def is_no_observation(value):
    return value is None or _text(value) in NO_OBSERVATION
