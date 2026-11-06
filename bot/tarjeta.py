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


def lista_fuente(tam):
    return _fuente("BarlowCondensed-Bold.ttf", tam)


# ----------------------------------------------------------------- la foto

def _cubrir(img, w, h, foco_y=0.38):
    """Escala y recorta para llenar w x h. foco_y decide qué parte se
    conserva al recortar en vertical: 0.38 deja la cara arriba, que es donde
    suele estar en una foto deportiva."""
    sw, sh = img.size
    escala = max(w / sw, h / sh)
    nw, nh = max(1, int(sw * escala)), max(1, int(sh * escala))
    img = img.resize((nw, nh), Image.LANCZOS)
    izq = max(0, (nw - w) // 2)
    arriba = max(0, min(int((nh - h) * foco_y), nh - h))
    return img.crop((izq, arriba, izq + w, arriba + h))


def _aura(panel, color):
    """Borde de luz de neón alrededor del sujeto.

    Sin un modelo de segmentación no se puede recortar al jugador. Pero en
    una foto deportiva el sujeto es casi siempre lo más brillante, así que se
    toma esa zona, se le saca el CONTORNO (dilatar menos erosionar) y se
    ilumina solo ahí. Teñir toda la zona brillante, que fue el primer
    intento, dejaba al jugador rosa.
    """
    gris = panel.convert("L")
    brillo = gris.point(lambda v: 255 if v > 145 else 0)
    contorno = ImageChops.difference(brillo.filter(ImageFilter.MaxFilter(9)),
                                     brillo.filter(ImageFilter.MinFilter(9)))
    contorno = contorno.filter(ImageFilter.GaussianBlur(config.TARJETA_AURA_RADIO))
    capa = Image.new("RGB", panel.size, color)
    capa.putalpha(contorno.point(
        lambda v: int(v * config.TARJETA_AURA_FUERZA)))
    base = panel.convert("RGBA")
    base.alpha_composite(capa)
    return ImageChops.screen(panel, Image.composite(
        Image.new("RGB", panel.size, color), Image.new("RGB", panel.size, (0, 0, 0)),
        contorno.point(lambda v: int(v * config.TARJETA_AURA_FUERZA))))


def panel_foto(img, w, h):
    panel = _cubrir(img.convert("RGB"), w, h)
    panel = ImageEnhance.Contrast(panel).enhance(1.12)
    panel = ImageEnhance.Color(panel).enhance(1.15)
    if config.TARJETA_AURA:
        panel = _aura(panel, config.COLOR_AURA)
    return panel


# ------------------------------------------------------------ el fondo izq

def _fondo(w, h):
    """Degradado oscuro con unas luces desenfocadas, como un estadio."""
    base = Image.new("RGB", (w, h), config.COLOR_FONDO_2)
    grad = Image.new("L", (1, h))
    for y in range(h):
        grad.putpixel((0, y), int(255 * (y / max(h - 1, 1)) ** 0.85))
    grad = grad.resize((w, h))
    base = Image.composite(Image.new("RGB", (w, h), config.COLOR_FONDO_2),
                           Image.new("RGB", (w, h), config.COLOR_FONDO_1), grad)

    luces = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(luces)
    import random
    rng = random.Random(7)
    for _ in range(26):
        x, y = rng.randrange(w), rng.randrange(int(h * 0.42))
        r = rng.randrange(5, 17)
        tono = rng.choice([(255, 236, 190), (190, 215, 255), (255, 210, 170)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=tono)
    luces = luces.filter(ImageFilter.GaussianBlur(13))
    return Image.blend(base, Image.blend(base, luces, 0.5), 0.5)


# --------------------------------------------------------------- el texto

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


def _capa_glow(size, renglones, fuente, x, y0, alto_renglon, espacio):
    """Todas las palabras resaltadas en una sola capa, para fundirla de golpe.

    Se funde con modo PANTALLA (aditivo): así el resplandor solo ilumina y
    nunca oscurece lo que hay debajo. Mezclarla de forma normal, que fue el
    primer intento, apagaba el texto en vez de encenderlo.
    """
    capa = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(capa)
    y = y0
    hay = False
    for renglon in renglones:
        cursor = x
        for palabra, resaltada in renglon:
            w = d.textbbox((0, 0), palabra, font=fuente)[2]
            if resaltada:
                d.text((cursor, y), palabra, font=fuente, fill=config.COLOR_RESALTE)
                hay = True
            cursor += w + espacio
        y += alto_renglon
    if not hay:
        return None
    capa = capa.filter(ImageFilter.GaussianBlur(config.TARJETA_GLOW_RADIO))
    return ImageEnhance.Brightness(capa).enhance(config.TARJETA_GLOW_FUERZA)


def _dibuja_texto(draw, renglones, fuente, x, y0, alto_renglon, espacio):
    """Dibuja el titular nítido encima del resplandor."""
    y = y0
    for renglon in renglones:
        cursor = x
        for palabra, resaltada in renglon:
            w = draw.textbbox((0, 0), palabra, font=fuente)[2]
            # El núcleo va más claro que el halo: así se lee como neón de
            # verdad en vez de como una mancha de color.
            draw.text((cursor, y), palabra, font=fuente,
                      fill=config.COLOR_RESALTE_NUCLEO if resaltada
                      else config.COLOR_TEXTO)
            cursor += w + espacio
        y += alto_renglon


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

def componer(foto, titulo, resaltar=None, lista=None, logo_path=None):
    """Devuelve la tarjeta 4:5 lista para publicar."""
    W, H = config.CANVAS_W, config.CANVAS_H
    ancho_txt = int(W * config.TARJETA_PROPORCION_TEXTO)
    ancho_foto = W - ancho_txt
    margen = config.TARJETA_MARGEN

    lienzo = Image.new("RGB", (W, H), config.COLOR_FONDO_1)
    lienzo.paste(_fondo(ancho_txt, H), (0, 0))
    lienzo.paste(panel_foto(foto, ancho_foto, H), (ancho_txt, 0))

    d = ImageDraw.Draw(lienzo)

    util = ancho_txt - margen * 2
    lista = [l for l in (lista or []) if l.strip()]

    # Sin lista hay más espacio, así que el titular puede arrancar más grande
    tope = (config.TARJETA_TITULAR_MAX if lista
            else config.TARJETA_TITULAR_MAX_SOLO)

    marcadas = _marca_resaltadas(titulo, resaltar)
    for tam in range(tope, config.TARJETA_TITULAR_MIN - 1, -2):
        f = titular(tam)
        renglones = _acomoda(d, marcadas, f, util)
        alto_renglon = int(tam * config.TARJETA_INTERLINEA)
        alto_t = len(renglones) * alto_renglon
        tam_l = max(config.TARJETA_LISTA_MIN, int(tam * config.TARJETA_LISTA_RATIO))
        alto_fila = int(tam_l * 1.45)
        alto_l = (len(lista) * alto_fila + config.TARJETA_HUECO_LISTA) if lista else 0
        cabe_alto = alto_t + alto_l <= H - margen * 2 - config.TARJETA_LOGO_ALTO - 30
        if cabe_alto and not _desborda(d, renglones, f, util):
            break

    # El bloque va centrado verticalmente, con un sesgo hacia arriba
    libre = H - margen * 2 - config.TARJETA_LOGO_ALTO - 30 - (alto_t + alto_l)
    y0 = margen + int(libre * config.TARJETA_SESGO_VERTICAL)
    espacio = _ancho(d, " ", f)

    glow = _capa_glow(lienzo.size, renglones, f, margen, y0, alto_renglon, espacio)
    if glow is not None:
        lienzo = ImageChops.screen(lienzo, glow)
    d = ImageDraw.Draw(lienzo)
    d.rectangle([ancho_txt - 4, 0, ancho_txt, H], fill=config.COLOR_RESALTE)

    _dibuja_texto(d, renglones, f, margen, y0, alto_renglon, espacio)

    if lista:
        y = y0 + alto_t + config.TARJETA_HUECO_LISTA
        fl = lista_fuente(tam_l)
        for fila in lista:
            d.text((margen, y), fila.upper(), font=fl, fill=config.COLOR_LISTA)
            y += alto_fila

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            lw, lh = logo.size
            esc = min(config.TARJETA_LOGO_ALTO / lh, (ancho_txt * 0.5) / lw)
            logo = logo.resize((max(1, int(lw * esc)), max(1, int(lh * esc))),
                               Image.LANCZOS)
            lienzo.paste(logo, (margen, H - margen - logo.size[1]), logo)
        except Exception:
            pass

    return lienzo


# ------------------------------------------------- ¿foto o gráfica de stats?

def _senales(img):
    """Mide qué tan 'plana' es una imagen.

    Una tarjeta de estadísticas tiene fondos lisos, pocos colores y bordes
    duros. Una foto tiene degradados, ruido y muchísimos colores.
    """
    chica = img.convert("RGB").resize((160, 160), Image.LANCZOS)
    # Cuantizar y ver qué tanto domina un puñado de colores
    q = chica.quantize(colors=64, method=Image.MEDIANCUT).convert("RGB")
    cuenta = sorted((c for c, _ in q.getcolors(160 * 160)), reverse=True)
    total = 160 * 160
    dominio = sum(cuenta[:6]) / total          # 1.0 = todo son 6 colores
    distintos = len(chica.getcolors(maxcolors=160 * 160) or [])
    # Planicie local: qué fracción de píxeles es idéntica a su vecino
    gris = chica.convert("L")
    bordes = ImageChops.difference(gris, gris.filter(ImageFilter.MinFilter(3)))
    hist = bordes.histogram()
    plano = sum(hist[:3]) / total
    return dominio, distintos / total, plano


def es_grafica(img):
    """True si la imagen parece una tarjeta de estadísticas y no una foto.

    Ante la duda se responde que SÍ es gráfica, porque los costos del error
    no son simétricos: tratar una gráfica como foto la parte a la mitad y la
    vuelve ilegible, mientras que tratar una foto como gráfica solo hace que
    se use el diseño anterior, que se ve bien.
    """
    try:
        dominio, variedad, plano = _senales(img)
    except Exception:
        return True
    puntos = 0
    if dominio > config.GRAFICA_DOMINIO:   puntos += 1
    if variedad < config.GRAFICA_VARIEDAD: puntos += 1
    if plano > config.GRAFICA_PLANICIE:    puntos += 1
    return puntos >= 2
