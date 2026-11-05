"""Escribe el caption con un modelo de IA, a partir del texto del tweet.

Tres reglas de oro:

1. NUNCA inventa datos. El modelo recibe instrucciones estrictas de usar solo
   lo que viene en el texto original, y además el resultado se valida: si
   aparece un número que no estaba en la fuente, se descarta.

2. NUNCA bloquea la publicación. Si la API falla, se tarda o devuelve algo
   que no pasa las validaciones, se usa el texto original tal cual.

3. NUNCA le pone tono alegre a una mala noticia. Cuando el clasificador
   detecta lesión, castigo, despido o fallecimiento, el modelo recibe la
   instrucción de ser sobrio y no cerrar con pregunta.
"""
import os
import random
import re

import requests

from . import config, emojis

URL = "https://api.anthropic.com/v1/messages"

INSTRUCCIONES = """You write Facebook captions for "Now Football", an NFL page with a US audience.

Rewrite the source post into a Facebook caption.

HARD RULES — breaking any of these makes the caption unusable:
- Use ONLY facts present in the source. Never add a number, name, team, date or claim that is not there.
- Never change a number that is in the source.
- Write in English.
- No hashtags. No @mentions. No links.
- Do not start with an emoji.
- Maximum 2 short paragraphs. Under 300 characters total.

STYLE:
- Open with a hook that makes someone stop scrolling. Lead with the most striking fact.
- Plain, confident sports-page voice. No hype words like "INSANE" or "YOU WON'T BELIEVE".
- At most 2 emojis inside the text, and only where they fit naturally.

Reply with the caption only. No preamble, no quotes around it."""

SOBRIO = """
THIS IS SERIOUS NEWS (injury, suspension, firing or death).
Be factual and respectful. No emojis. No hook language. No question at the end."""

PREGUNTA = """
End with one short question that invites fans to reply. Keep it natural, not forced."""


def _numeros(texto):
    """Números del texto, sin comas ni símbolos, para poder compararlos."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*", texto or "")}


def valida(salida, fuente):
    """Devuelve (sirve, motivo). Prefiere descartar ante la duda."""
    if not salida or len(salida.strip()) < 15:
        return False, "quedó vacío o demasiado corto"
    if len(salida) > config.IA_MAX_CARACTERES:
        return False, f"se pasó de largo ({len(salida)} caracteres)"
    if "#" in salida or "@" in salida or "http" in salida.lower():
        return False, "metió hashtags, menciones o enlaces"

    # Lo más importante: ningún número nuevo
    nuevos = _numeros(salida) - _numeros(fuente)
    # Se permiten los de una o dos cifras, que suelen ser parte del lenguaje
    # ("a 2-game stretch") y no datos duros.
    nuevos = {n for n in nuevos if len(n) > 2}
    if nuevos:
        return False, f"inventó números que no estaban en la fuente: {sorted(nuevos)}"
    return True, ""


def _pedir(prompt, api_key):
    r = requests.post(
        URL,
        headers={"x-api-key": api_key,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": config.IA_MODELO,
              "max_tokens": config.IA_MAX_TOKENS,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=config.IA_TIMEOUT,
    )
    r.raise_for_status()
    datos = r.json()
    partes = [b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text"]
    return "".join(partes).strip()


def escribe(texto_fuente, rng=None):
    """Devuelve (caption, nota). Si algo falla, devuelve el texto original."""
    rng = rng or random
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not config.USAR_IA:
        return texto_fuente, "IA apagada"
    if not api_key:
        return texto_fuente, "sin ANTHROPIC_API_KEY, se usa el texto original"

    sensible = emojis.es_sensible(texto_fuente)
    con_pregunta = (not sensible) and rng.random() < config.IA_PROB_PREGUNTA

    prompt = INSTRUCCIONES
    if sensible:
        prompt += SOBRIO
    elif con_pregunta:
        prompt += PREGUNTA
    prompt += f"\n\nSOURCE POST:\n{texto_fuente}"

    try:
        salida = _pedir(prompt, api_key)
    except Exception as e:
        return texto_fuente, f"la IA no respondió ({type(e).__name__}), se usa el original"

    sirve, motivo = valida(salida, texto_fuente)
    if not sirve:
        return texto_fuente, f"se descartó lo que escribió la IA: {motivo}"

    nota = "escrito por IA"
    if sensible:
        nota += ", tono sobrio"
    elif con_pregunta:
        nota += ", con pregunta"
    return salida, nota
