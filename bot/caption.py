"""Arma el caption: texto original limpio + crédito + hashtags."""
import re

from . import config

TCO = re.compile(r"https?://t\.co/\S+")
MULTISPACE = re.compile(r"\n{3,}")


def clean(text):
    text = TCO.sub("", text or "")
    text = MULTISPACE.sub("\n\n", text)
    return text.strip()


def build(tweet):
    body = clean(tweet.get("text", ""))
    credit = config.CREDIT_TEMPLATE.format(author=tweet.get("author", ""))
    parts = [p for p in (body, credit, config.HASHTAGS) if p]
    return "\n\n".join(parts)
