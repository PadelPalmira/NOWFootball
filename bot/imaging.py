"""Baja la imagen del tweet y la arma en formato 4:5 para Facebook.

Hay dos diseños y aquí se decide cuál toca:

  PANTALLA PARTIDA  foto del jugador a la derecha, titular y lista a la
                    izquierda. Para las cuentas aprobadas que publican
                    fotos limpias.

  VERTICAL          imagen completa al centro, titular arriba y logo
                    abajo. Para todo lo demás. La imagen nunca se recorta
                    ni se parte, así que sirve igual para una gráfica de
                    estadísticas que para una captura de pantalla, y la
                    explicación queda arriba con la misma tipografía.
"""
import io
import os
import requests
from PIL import Image

from . import config, estructura, redactor, tarjeta


def download(url, timeout=45):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NowFootballBot/1.0)"}
    r = requests.get(url, timeout=timeout, headers=headers)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def build(url, out_path, logo_path=None, texto=None, autor=None, verboso=False):
    """Descarga la imagen y arma la publicación.

    Si la imagen es una FOTO, se arma la tarjeta de pantalla partida con el
    texto a la izquierda. Si ya es una GRÁFICA de estadísticas, partirla la
    volvería ilegible, así que se usa el diseño vertical: la imagen entera
    al centro, el titular arriba y el logo abajo.

    Devuelve (ruta, imagen_original_sin_tocar). La original se devuelve sin
    tocar porque es la que se usa para detectar repetidas: así la huella no
    cambia aunque cambie el diseño.
    """
    original = download(url)
    logo = logo_path if logo_path is not None else config.LOGO_PATH

    aprobada = (autor or "").lstrip("@").lower() in {
        c.lstrip("@").lower() for c in config.CUENTAS_TARJETA}

    usar_tarjeta = False
    motivo = ""
    if not config.USAR_TARJETA:
        motivo = "la tarjeta está apagada en config"
    elif not aprobada:
        motivo = f"@{autor} no está en CUENTAS_TARJETA"
    elif not texto:
        motivo = "el tweet no trae texto"
    else:
        titulo, lista, _ = estructura.analiza(texto)
        if not titulo:
            motivo = "no se pudo sacar un titular"
        elif not config.TARJETA_SIEMPRE and tarjeta.es_grafica(original):
            motivo = "la imagen ya es una gráfica, se deja completa"
        else:
            usar_tarjeta = True

    if usar_tarjeta:
        resaltar, nota = redactor.resaltado(titulo)
        if verboso:
            print(f"    Imagen: pantalla partida · {nota}")
        armada = tarjeta.componer(original, titulo, resaltar, lista, logo)
    else:
        # Diseño vertical: la imagen entera, con el titular arriba y el logo
        # abajo. Nunca se recorta ni se parte, así que sirve igual para una
        # gráfica de estadísticas que para una captura de pantalla.
        titulo2, _, _ = estructura.analiza(texto or "")
        if titulo2:
            resaltar, nota = redactor.resaltado(titulo2)
            if verboso:
                print(f"    Imagen: vertical, imagen completa · {motivo} · {nota}")
            armada = tarjeta.componer_vertical(original, titulo2, resaltar, logo)
        else:
            if verboso:
                print(f"    Imagen: vertical sin titular · {motivo}")
            armada = tarjeta.componer_vertical(original, "", None, logo)

    armada.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path, original
