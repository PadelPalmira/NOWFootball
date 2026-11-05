"""Elige un emoji según de qué trata la publicación.

La regla más importante de este archivo es la de abajo del todo: las malas
noticias se revisan PRIMERO. Un 🔥 sobre una lesión o un fallecimiento es
mucho peor que no poner emoji, así que esas categorías se atrapan antes de
que cualquier otra regla alcance a disparar.
"""
import re

# El orden importa: gana la primera categoría que coincida.
CATEGORIAS = [
    # --- Sensibles. Van primero, siempre.
    ("luto",     ["dies", "died", "death", "passed away", "passing of",
                  "funeral", "memorial", "tragedy"],                      ""),
    ("lesion",   ["injury", "injured", "out for the season", "torn", "acl",
                  "mcl", "achilles", "surgery", "concussion", "ir ",
                  "placed on ir", "questionable", "doubtful", "ruled out",
                  "carted off", "hospital"],                              "🚑"),
    ("castigo",  ["suspended", "suspension", "arrested", "charged",
                  "investigation", "fined", "violation", "banned"],       "⚖️"),
    ("despido",  ["fired", "released", "cut ", "waived", "benched",
                  "steps down", "resigns"],                              "📉"),

    # --- Positivas y neutras
    # "most" a secas aparece en cualquier tabla de líderes, así que el récord
    # necesita frases más específicas para no quedarse con todo.
    ("record",   ["record", "all-time", "first ever", "first player",
                  "nfl history", "in history", "milestone", "becomes the",
                  "most ever", "most in nfl", "youngest", "oldest",
                  "fastest to", " ever "],                                         "👑"),
    ("racha",    ["streak", "undefeated", "clinch", "playoff berth",
                  "in a row", "straight win", "straight game",
                  "have won", "has won", "perfect season", "sweep"],      "🔥"),
    ("dramatico",["comeback", "walk-off", "overtime", "game-winning",
                  "buzzer", "hail mary", "upset", "stunner", "thriller"], "😱"),
    ("dinero",   ["contract", "extension", "million", "guaranteed",
                  "deal worth", "$"],                                    "💰"),
    ("movimiento",["trade", "traded", "signs", "signed", "acquire",
                  "agrees to", "joins the"],                             "🔄"),
    ("draft",    ["draft", "first-round", "no. 1 pick",
                  "prospect", "combine"],                                "🎯"),
    ("anotacion",["touchdown", " td", "touchdowns", "scores", "scoring",
                  "end zone", "field goal"],                             "🏈"),
    ("defensa",  ["sack", "interception", "pick-six", "fumble",
                  "turnover", "tackle"],                                 "🛡️"),
    ("stats",    ["yards", "leaders", "passing", "rushing", "receiving",
                  "completions", "stats", "ranks", "averaging", "per game",
                  "leads the league"],                                   "📊"),
]

POR_DEFECTO = "🏈"


def categoria(texto):
    t = " " + (texto or "").lower() + " "
    for nombre, claves, _ in CATEGORIAS:
        for clave in claves:
            if clave in t:
                return nombre
    return "general"


def para(texto):
    """Devuelve el emoji que le toca al texto. Puede ser cadena vacía."""
    t = " " + (texto or "").lower() + " "
    for _, claves, emoji in CATEGORIAS:
        for clave in claves:
            if clave in t:
                return emoji
    return POR_DEFECTO


def es_sensible(texto):
    return categoria(texto) in ("luto", "lesion", "castigo", "despido")
