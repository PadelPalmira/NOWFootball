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
    """Descarga la imagen del tweet y arma la tarjeta 4:5 de Now Football.

    Devuelve (ruta_de_la_tarjeta, imagen_original). La original se devuelve
    SIN TOCAR porque es sobre ella que se calcula la huella que impide
    republicar: si se calculara sobre la tarjeta ya armada, cambiar el
    diseño haría que todo el historial dejara de reconocerse.

    Ya no hay que decidir entre diseños. Todas las cuentas reciben la misma
    tarjeta blanca y la imagen nunca se recorta.
    """
    original = download(url)

    titulo, _lista, _cola = estructura.analiza(texto or "")
    resaltar, nota = (None, "sin titular")
    if titulo:
        resaltar, nota = redactor.resaltado(titulo)
        if not resaltar:
            resaltar = estructura.resalte_por_reglas(titulo)
            nota = "reglas"

    if verboso:
        if titulo:
            print(f"    Imagen: tarjeta blanca · resaltado por {nota}")
        else:
            print("    Imagen: tarjeta blanca · el tweet no trae titular")

    armada = tarjeta.componer_blanco(original, titulo or "", resaltar,
                                     logo_path or config.LOGO_PATH)
    armada.save(out_path, "JPEG", quality=92, optimize=True)
    return out_path, original
