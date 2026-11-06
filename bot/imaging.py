"""Convierte cualquier imagen a lienzo 4:5 listo para Facebook.

Usa padding, nunca recorte: las tarjetas de stats traen números y texto que un
crop centrado cortaría. Para que el 4:5 no quede con espacio muerto, el fondo
es la misma imagen ampliada y desenfocada (el recurso clásico de Instagram),
con el logo de Now Football en la franja inferior.
"""
import io
import os
import requests
from PIL import Image, ImageEnhance, ImageFilter

from . import config, estructura, redactor, tarjeta


def download(url, timeout=45):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NowFootballBot/1.0)"}
    r = requests.get(url, timeout=timeout, headers=headers)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def _cover(img, w, h):
    """Escala y recorta para cubrir por completo un lienzo w x h."""
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _backdrop(src, w, h):
    bg = _cover(src, w, h).filter(ImageFilter.GaussianBlur(config.BLUR_RADIUS))
    bg = ImageEnhance.Brightness(bg).enhance(config.BLUR_DARKEN)
    bg = ImageEnhance.Color(bg).enhance(config.BLUR_SATURATION)
    return bg


def to_4x5(img, logo_path=None, bg=None):
    bg_color = bg or config.BG_COLOR
    logo_path = logo_path if logo_path is not None else config.LOGO_PATH

    cw, ch = config.CANVAS_W, config.CANVAS_H
    src = img.convert("RGB")

    # --- Fondo
    if config.BLUR_BACKDROP:
        canvas = _backdrop(src, cw, ch)
    else:
        canvas = Image.new("RGB", (cw, ch), bg_color)

    logo = None
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
        except Exception:
            logo = None

    strip = config.LOGO_STRIP_H if logo else 0
    margin = config.SIDE_MARGIN

    # --- Capa nítida: lo más grande posible sin recortar ni invadir la franja
    avail_w = cw - 2 * margin
    avail_h = ch - strip - 2 * margin
    sw, sh = src.size
    scale = min(avail_w / sw, avail_h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    sharp = src.resize((nw, nh), Image.LANCZOS)

    x = (cw - nw) // 2
    y = margin + (avail_h - nh) // 2

    # Borde sutil para despegar la imagen del fondo desenfocado
    if config.BLUR_BACKDROP:
        pad = config.EDGE_PAD
        marco = Image.new("RGB", (nw + pad * 2, nh + pad * 2), config.EDGE_COLOR)
        canvas.paste(marco, (x - pad, y - pad))
    canvas.paste(sharp, (x, y))

    # --- Logo
    if logo:
        lw, lh = logo.size
        lscale = min(config.LOGO_MAX_H / lh, (cw * 0.5) / lw)
        logo = logo.resize((max(1, int(lw * lscale)), max(1, int(lh * lscale))), Image.LANCZOS)
        lx = (cw - logo.size[0]) // 2
        ly = ch - strip + (strip - logo.size[1]) // 2
        canvas.paste(logo, (lx, ly), logo)

    return canvas


def build(url, out_path, logo_path=None, texto=None, autor=None, verboso=False):
    """Descarga la imagen y arma la publicación.

    Si la imagen es una FOTO, se arma la tarjeta de pantalla partida con el
    texto a la izquierda. Si ya es una GRÁFICA de estadísticas, partirla la
    volvería ilegible, así que se usa el lienzo 4:5 con fondo desenfocado.

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
            print(f"    Imagen: tarjeta de pantalla partida · {nota}")
        armada = tarjeta.componer(original, titulo, resaltar, lista, logo)
    else:
        if verboso:
            print(f"    Imagen: lienzo 4:5 con fondo desenfocado · {motivo}")
        armada = to_4x5(original, logo_path=logo)

    armada.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path, original
