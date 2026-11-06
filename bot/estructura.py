"""Parte el texto de un tweet en titular y lista, para la tarjeta.

Esto se hace con reglas, no con IA, a propósito: la lista trae nombres y
números que deben salir EXACTOS. Un modelo que reescribe es un riesgo
innecesario cuando un par de expresiones regulares resuelven bien.
"""
import re
import unicodedata

# Dos formas de renglón de lista:
#   con marcador    "1. Bo Nix - 15"  "T-3. Jared Goff - 10"  "- Wilson"  "• X"
#   sin marcador    "Tee Higgins - 155"   <- la que más usan @NFL_Stats y
#                                            @polymarketblitz, y que la
#                                            primera versión tiraba a la basura
CON_MARCADOR = re.compile(r"^\s*(?:[-–—•*]\s+|T?-?\d+[\.\)]\s+|\d+\s*[-–]\s+)")
NOMBRE_CIFRA = re.compile(r"^\s*\S.{0,44}?\s[-–—]\s*[\d,\.]+\s*\)?\s*$")


def es_item(linea):
    return bool(CON_MARCADOR.match(linea) or NOMBRE_CIFRA.match(linea))
TCO = re.compile(r"https?://\S+")
SOLO_EMOJI = re.compile(
    r"^[\s\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+$")


def normaliza(texto):
    """Convierte las letras decorativas a letras normales.

    Varias de las cuentas escriben titulares con caracteres matemáticos
    (𝗧𝗥𝗘𝗡𝗗𝗜𝗡𝗚, 𝐓𝐇𝐄 𝐑𝐀𝐕𝐄𝐍𝐒). Esos signos no existen en Anton ni en Barlow,
    así que en la tarjeta saldrían como cuadritos vacíos. NFKC los baja a
    letras normales sin cambiar el texto.
    """
    return unicodedata.normalize("NFKC", texto or "")


def limpia(texto):
    return TCO.sub("", normaliza(texto)).strip()


def analiza(texto):
    """Devuelve (titular, lista, cola).

    titular : el encabezado, lo que va grande en la tarjeta
    lista   : los renglones enumerados, tal cual venían
    cola    : comentario final que no se usa en la tarjeta
    """
    lineas = [l.strip() for l in limpia(texto).splitlines()]
    lineas = [l for l in lineas if l and not SOLO_EMOJI.match(l)]
    if not lineas:
        return "", [], ""

    titulo, lista, cola = [], [], []
    for linea in lineas:
        if es_item(linea):
            lista.append(linea)
        elif lista:
            cola.append(linea)          # lo que viene después de la lista
        else:
            titulo.append(linea)

    # Sin lista: el primer párrafo es el titular y el resto es cola
    if not lista and len(titulo) > 1:
        cola = titulo[1:]
        titulo = titulo[:1]

    return " ".join(titulo).strip(), lista, " ".join(cola).strip()


PALABRAS_VACIAS = {
    "the","a","an","of","in","on","at","to","for","with","and","or","but",
    "is","are","was","were","be","been","has","have","had","his","her","its",
    "their","this","that","these","those","so","far","since","after","before",
    "than","as","by","from","he","she","they","it","who","what","all","more",
    "most","no","not","now","out","up","over","per","into","about",
}


ES_EMOJI = re.compile(
    r"^[\s\U0001F300-\U0001FAFF\U00002600-\U000027BF"
    r"\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF\uFE0F]+$")


def resalte_por_reglas(titulo, maximo=3):
    """Elige qué resaltar sin usar IA: la racha más larga de palabras con
    contenido. Es el respaldo para cuando la IA no está disponible.

    Se saltan los emojis y las palabras huecas. Resaltar un 🚨 no aporta
    nada y además esos signos arrastran el resplandor del neón.
    """
    palabras = titulo.split()
    mejor, actual = [], []
    for p in palabras:
        limpio = p.strip(".,:;!?\"'\u201c\u201d").lower()
        util = (limpio and limpio not in PALABRAS_VACIAS
                and not ES_EMOJI.match(p) and any(c.isalnum() for c in limpio))
        if util:
            actual.append(p)
            if len(actual) > len(mejor):
                mejor = list(actual)
        else:
            actual = []
    if not mejor:
        return []
    frase = " ".join(mejor[:maximo])
    return [frase.rstrip(":;,.")] if frase.rstrip(":;,.") else []
