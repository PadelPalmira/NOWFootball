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

from . import config


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


def build(url, out_path, logo_path=None):
    """Descarga, convierte y guarda. Devuelve (ruta, imagen_original_sin_tocar)."""
    original = download(url)
    framed = to_4x5(original, logo_path=logo_path)
    framed.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path, original
