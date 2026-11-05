"""Arma el texto de la publicación.

Formato fijo de Now Football:

    #NFL  |  🏈 Texto de la publicación

    📊 via @NFL_Stats

    #NowFootball #NFLStats

El "#NFL  |  " de arriba es la marca de la página y va en todas. El resto
de los hashtags van hasta abajo y rotan, para que el pie de los posts no
sea siempre idéntico.
"""
import random
import re

from . import config, emojis, redactor

TCO = re.compile(r"https?://t\.co/\S+")
MULTISPACE = re.compile(r"\n{3,}")
EMOJI_INICIAL = re.compile(
    "^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF←-⇿⬀-⯿]+\\s*")


def clean(text):
    text = TCO.sub("", text or "")
    text = MULTISPACE.sub("\n\n", text)
    return text.strip()


def hashtags(rng=None):
    """Los de abajo. El #NFL ya va arriba, así que aquí no se repite."""
    rng = rng or random
    etiquetas = [h for h in config.HASHTAG_FIJOS if h.lower() != config.HASHTAG_MARCA.lower()]
    minimo, maximo = config.HASHTAG_EXTRA
    bolsa = [h for h in config.HASHTAG_BOLSA
             if h not in etiquetas and h.lower() != config.HASHTAG_MARCA.lower()]
    etiquetas += rng.sample(bolsa, min(rng.randint(minimo, maximo), len(bolsa)))
    return " ".join(etiquetas)


def credito(autor, rng=None):
    rng = rng or random
    return rng.choice(config.CREDITO_VARIANTES).format(author=autor)


def encabezado(texto, rng=None):
    """La primera línea: la marca, el separador y el texto con su emoji.

    El emoji se elige con el clasificador propio, no lo pone la IA: así la
    garantía de que una mala noticia nunca lleve emoji alegre se mantiene
    aunque el modelo escriba otra cosa.
    """
    cuerpo = clean(texto)
    if config.USAR_EMOJIS:
        # Si el tweet ya traía emoji al inicio, no le encimamos otro
        if not EMOJI_INICIAL.match(cuerpo):
            emoji = emojis.para(cuerpo)
            if emoji:
                cuerpo = f"{emoji} {cuerpo}"
    return f"{config.HASHTAG_MARCA}{config.SEPARADOR_MARCA}{cuerpo}"


def build(tweet, rng=None, verboso=False):
    rng = rng or random
    original = clean(tweet.get("text", ""))

    cuerpo, nota = redactor.escribe(original, rng)
    if verboso:
        print(f"    Caption: {nota}")

    # El emoji se decide siempre con el texto ORIGINAL: es el que trae los
    # términos crudos del tweet y el clasificador es más confiable con él.
    emoji = ""
    if config.USAR_EMOJIS and not EMOJI_INICIAL.match(cuerpo):
        emoji = emojis.para(original)
    cabeza = f"{config.HASHTAG_MARCA}{config.SEPARADOR_MARCA}"
    cabeza += f"{emoji} {cuerpo}" if emoji else cuerpo

    partes = [cabeza, credito(tweet.get("author", ""), rng), hashtags(rng)]
    return "\n\n".join(p for p in partes if p)
