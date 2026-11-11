"""Arma la tarjeta 4:5 de Now Football: foto a la derecha, texto a la izquierda.

El diseño imita el que se venía haciendo a mano: pantalla partida, la foto
del jugador a la derecha con un halo de neón, y a la izquierda el titular en
mayúsculas con las palabras clave resaltadas, más la lista si el tweet la
trae.

Todo se dibuja con tipografía real, no se genera con IA. Eso importa: en una
página de estadísticas un número mal escrito es inaceptable, y los modelos de
imagen todavía se equivocan al dibujar texto. Aquí los números salen
exactamente como venían en la fuente.
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from . import config

FUENTES = os.path.join("assets", "fonts")


def _fuente(nombre, tam):
    ruta = os.path.join(FUENTES, nombre)
    if os.path.exists(ruta):
        return ImageFont.truetype(ruta, tam)
    for alterna in ("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(alterna):
            return ImageFont.truetype(alterna, tam)
    return ImageFont.load_default()


def titular(tam):
    return _fuente("Anton-Regular.ttf", tam)


def _ancho(draw, texto, fuente):
    return draw.textbbox((0, 0), texto, font=fuente)[2]


def _parte_larga(draw, palabra, fuente, max_ancho):
    """Parte una palabra que no cabe ni sola en un renglón.

    Primero por la diagonal o el guion, que es donde se parte natural
    ("RECEIVING/RUSHING"). Si aun así no cabe, se corta a lo bruto.
    """
    if _ancho(draw, palabra, fuente) <= max_ancho:
        return [palabra]
    for sep in ("/", "-", "\u2013"):
        if sep in palabra[1:-1]:
            trozos, acum = [], ""
            for parte in palabra.split(sep):
                cand = (acum + sep + parte) if acum else parte
                if acum and _ancho(draw, cand + sep, fuente) > max_ancho:
                    trozos.append(acum + sep)
                    acum = parte
                else:
                    acum = cand
            if acum:
                trozos.append(acum)
            salida = []
            for t in trozos:
                salida.extend(_parte_larga(draw, t, fuente, max_ancho))
            return salida
    # corte duro, carácter por carácter
    salida, acum = [], ""
    for ch in palabra:
        if acum and _ancho(draw, acum + ch, fuente) > max_ancho:
            salida.append(acum)
            acum = ch
        else:
            acum += ch
    if acum:
        salida.append(acum)
    return salida


def _acomoda(draw, palabras, fuente, max_ancho):
    """Reparte las palabras en renglones que quepan. Devuelve renglones de
    (palabra, resaltada)."""
    # Primero se parten las palabras que no caben ni solas
    sueltas = []
    for palabra, resaltada in palabras:
        for trozo in _parte_larga(draw, palabra, fuente, max_ancho):
            sueltas.append((trozo, resaltada))

    renglones, actual = [], []
    for palabra, resaltada in sueltas:
        prueba = " ".join(p for p, _ in actual + [(palabra, resaltada)])
        if actual and _ancho(draw, prueba, fuente) > max_ancho:
            renglones.append(actual)
            actual = [(palabra, resaltada)]
        else:
            actual.append((palabra, resaltada))
    if actual:
        renglones.append(actual)
    return renglones


def _desborda(draw, renglones, fuente, max_ancho):
    """True si algún renglón se sale del panel."""
    for r in renglones:
        if _ancho(draw, " ".join(p for p, _ in r), fuente) > max_ancho:
            return True
    return False


def _marca_resaltadas(titulo, resaltar):
    """Convierte el titular en [(palabra, resaltada)] según las frases a
    resaltar."""
    palabras = titulo.upper().split()
    marcadas = [[p, False] for p in palabras]
    for frase in (resaltar or []):
        objetivo = frase.upper().split()
        if not objetivo:
            continue
        for i in range(len(palabras) - len(objetivo) + 1):
            trozo = [palabras[j].strip(".,:;!?") for j in range(i, i + len(objetivo))]
            if trozo == [o.strip(".,:;!?") for o in objetivo]:
                for j in range(i, i + len(objetivo)):
                    marcadas[j][1] = True
    return [(p, r) for p, r in marcadas]


# ------------------------------------------------------------------ armado

def _contener(img, w, h):
    """Escala para que la imagen quepa COMPLETA en w x h, sin recortar nada."""
    sw, sh = img.size
    escala = min(w / sw, h / sh)
    return img.resize((max(1, int(sw * escala)), max(1, int(sh * escala))),
                      Image.LANCZOS)

# ------------------------------------------------------------------ armado

BLANCO = (255, 255, 255)


def _logo_ajustado(logo_path, alto):
    """Logo recortado a su dibujo real y escalado a `alto` de verdad.

    El archivo del logo es de 2048x2048 pero el dibujo solo ocupa el centro:
    alrededor hay aire transparente. Escalar el archivo tal cual dejaba el
    logo VISIBLE en unos 32 px aunque la config dijera 54. Por eso se veía
    casi indistinguible. Recortando el aire primero, el alto que se pide es
    el alto que se ve.
    """
    if not logo_path or not os.path.exists(logo_path):
        return None
    try:
        im = Image.open(logo_path).convert("RGBA")
    except Exception:
        return None
    caja = im.getchannel("A").getbbox()
    if caja:
        im = im.crop(caja)
    w, h = im.size
    if w <= 0 or h <= 0:
        return None
    return im.resize((max(1, int(w * alto / h)), max(1, alto)), Image.LANCZOS)


def componer_blanco(foto, titulo, resaltar=None, logo_path=None):
    """El diseño de Now Football: fondo blanco, titular arriba, imagen
    completa al centro y el logo en una franja oscura abajo.

    Es el ÚNICO diseño. La imagen nunca se recorta ni se parte: se escala
    hasta donde quepa y lo que sobra queda en blanco.

    Por qué así:

    - Se eliminó la pantalla partida. Recortaba tanto la imagen que el post
      ya no se parecía al original: un meme de "TRASH vs GARBAGE" acababa
      mostrando "H GAR" y medio bote de basura.
    - Se eliminó el vertical oscuro para que la página se vea pareja: un
      solo formato es más reconocible que dos.
    - La franja de abajo es oscura a propósito. El logo de Now Football es
      blanco con el balón de color, así que sobre el lienzo blanco
      desaparecía por completo. La franja le da el contraste que necesita y
      de paso cierra la tarjeta.
    """
    W, H = config.CANVAS_W, config.CANVAS_H
    margen = config.TARJETA_MARGEN
    util = W - margen * 2

    lienzo = Image.new("RGB", (W, H), BLANCO)
    d = ImageDraw.Draw(lienzo)

    logo = _logo_ajustado(logo_path, config.BLANCO_LOGO_ALTO)
    franja = config.BLANCO_FRANJA if logo else margen

    # El titular se achica solo hasta que quepa en los renglones permitidos.
    renglones, f, alto_renglon, alto_t = [], None, 0, 0
    if titulo:
        marcadas = _marca_resaltadas(titulo, resaltar)
        for tam in range(config.BLANCO_TITULAR_MAX, config.TARJETA_TITULAR_MIN - 1, -2):
            f = titular(tam)
            renglones = _acomoda(d, marcadas, f, util)
            alto_renglon = int(tam * config.TARJETA_INTERLINEA)
            alto_t = len(renglones) * alto_renglon
            if (len(renglones) <= config.BLANCO_MAX_RENGLONES
                    and not _desborda(d, renglones, f, util)):
                break

    bloque_texto = alto_t + margen if titulo else 0
    disponible = max(H - franja - margen - bloque_texto, 80)

    img = _contener(foto.convert("RGB"), W, disponible)
    sobra = max(0, (disponible - img.size[1]) // 2)
    y_texto = margen
    y_img = margen + bloque_texto + sobra
    x_img = (W - img.size[0]) // 2
    lienzo.paste(img, (x_img, y_img))

    # Filo tenue para que una imagen de fondo claro no se funda con el lienzo.
    filo = config.BLANCO_FILO
    if img.size[0] >= W:
        d.rectangle([0, y_img, W, y_img], fill=filo)
        d.rectangle([0, y_img + img.size[1] - 1, W, y_img + img.size[1] - 1], fill=filo)
    else:
        d.rectangle([x_img, y_img, x_img + img.size[0] - 1,
                     y_img + img.size[1] - 1], outline=filo, width=1)

    # El titular va en tinta oscura; lo resaltado, en el rosa de la marca.
    # Aquí NO va el neón encendido: el glow se hizo para fondo oscuro y
    # sobre blanco solo ensucia las letras.
    if titulo and f is not None:
        espacio = _ancho(d, " ", f)
        y = y_texto
        for renglon in renglones:
            x = margen
            for palabra, resaltada in renglon:
                d.text((x, y), palabra, font=f,
                       fill=config.COLOR_RESALTE if resaltada else config.COLOR_TINTA)
                x += _ancho(d, palabra, f) + espacio
            y += alto_renglon

    if logo:
        d.rectangle([0, H - franja, W, H], fill=config.COLOR_FRANJA)
        lienzo.paste(logo, ((W - logo.size[0]) // 2,
                            H - franja + (franja - logo.size[1]) // 2), logo)
    return lienzo
