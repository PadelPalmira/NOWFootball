"""Arma el caption: texto original limpio + crédito + hashtags.

El crédito y los hashtags rotan en cada publicación. Mandar siempre el mismo
bloque de texto al final es una de las señales más claras de automatización.
"""
import random
import re

from . import config

TCO = re.compile(r"https?://t\.co/\S+")
MULTISPACE = re.compile(r"\n{3,}")


def clean(text):
    text = TCO.sub("", text or "")
    text = MULTISPACE.sub("\n\n", text)
    return text.strip()


def hashtags(rng=None):
    rng = rng or random
    etiquetas = list(config.HASHTAG_FIJOS)
    minimo, maximo = config.HASHTAG_EXTRA
    cuantos = rng.randint(minimo, maximo)
    bolsa = [h for h in config.HASHTAG_BOLSA if h not in etiquetas]
    etiquetas += rng.sample(bolsa, min(cuantos, len(bolsa)))
    return " ".join(etiquetas)


def credito(autor, rng=None):
    rng = rng or random
    plantilla = rng.choice(config.CREDITO_VARIANTES)
    return plantilla.format(author=autor)


def build(tweet, rng=None):
    rng = rng or random
    partes = [
        clean(tweet.get("text", "")),
        credito(tweet.get("author", ""), rng),
        hashtags(rng),
    ]
    return "\n\n".join(p for p in partes if p)
