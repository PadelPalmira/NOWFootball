"""Elige qué publicar: lo más caliente de la ventana de tiempo más reciente.

Dos ideas sostienen esto:

1. VENTANAS. Al momento de publicar se mira solo lo de las últimas 2 horas.
   Si ahí no hay nada que sirva, se abre a 4 horas, luego a 8, luego a 24.
   La primera ventana con material gana, así que lo que sale siempre es lo
   más fresco disponible.

2. TASA, no total. Dentro de una ventana de 2 horas, comparar reposts en
   crudo favorece al tweet más viejo: uno de hace 110 minutos tuvo cinco
   veces más tiempo de acumular que uno de hace 20. Por eso se mide
   reposts POR HORA. Cómo se comparan esas tasas entre cuentas lo decide
   config.PUNTUACION: "cruda" las compara tal cual (gana el mejor de las
   cuatro cuentas) y "normalizada" las compara contra lo típico de cada
   cuenta (reparte más parejo). Está en "cruda".
"""
import datetime as dt
import statistics

from . import config


def age_hours(tweet, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    created = dt.datetime.fromisoformat(tweet["created_at"])
    return (now - created).total_seconds() / 3600.0


def vetado(tweet):
    """True si el texto trae algo de la lista de palabras vetadas."""
    t = (tweet.get("text") or "").lower()
    return any(p.lower() in t for p in config.PALABRAS_VETADAS)


def engagement(tweet):
    """Tracción total: reposts y likes juntos, con el repost pesando más.

    Medir solo reposts no funcionaba con estas cuentas: la mitad de los
    candidatos empataba en 2 o 3 y el desempate salía casi al azar.
    """
    return (tweet.get("retweets", 0) * config.PESO_REPOST
            + tweet.get("likes", 0))


def tasa(tweet, now=None):
    """Engagement por hora, con un piso de edad para que lo recién salido no
    produzca números absurdos."""
    horas = max(age_hours(tweet, now), config.EDAD_MINIMA_HORAS)
    return engagement(tweet) / horas


def baselines(queue, now=None, horas_max=None):
    """Tasa típica (mediana) de cada cuenta.

    IMPORTANTE: se mide sobre el mismo tramo de edad para todas las cuentas.
    Si se tomara la cola completa, una cuenta que publica despacio tendría su
    cola llena de tweets viejos (de tasa baja por definición, porque la tasa
    es reposts entre horas), su mediana se hundiría y cualquier cosa que
    publicara saldría inflada frente a una cuenta que publica seguido.
    """
    horas_max = horas_max or max(config.VENTANAS_HORAS)
    buckets = {}
    for t in queue.values():
        if age_hours(t, now) <= horas_max:
            buckets.setdefault(t["author"], []).append(tasa(t, now))

    # Si una cuenta casi no publicó en ese tramo, la mediana sería ruido.
    # En ese caso se usa la mediana general como referencia.
    todas = [v for lista in buckets.values() for v in lista]
    general = max(statistics.median(todas), 0.5) if todas else 1.0

    salida = {}
    for autor, valores in buckets.items():
        salida[autor] = (max(statistics.median(valores), 0.5)
                         if len(valores) >= config.MIN_MUESTRA_BASE else general)
    return salida


def score(tweet, base, now=None):
    """Qué tan bueno es este tweet frente a los demás candidatos.

    Con PUNTUACION = "cruda" (lo que está puesto) se compara la tracción por
    hora tal cual, así que gana el mejor de LAS CUATRO cuentas sin importar
    de quién sea. Con "normalizada" cada tweet compite contra lo normal de su
    propia cuenta, lo que reparte más parejo pero deja que un tweet mediano
    de una cuenta chica le gane a un notición de una grande.
    """
    if getattr(config, "PUNTUACION", "normalizada") == "cruda":
        return tasa(tweet, now)
    return tasa(tweet, now) / max(base, 0.5)


def _elegibles(queue, skip_ids, ahora, limite_horas, bases):
    fuera = []
    for tid, t in queue.items():
        if tid in skip_ids:
            continue
        horas = age_hours(t, ahora)
        if horas > limite_horas or horas < 0:
            continue
        if engagement(t) < config.MIN_ENGAGEMENT:
            continue
        if t["author"] not in config.ACCOUNTS:
            continue        # cuenta retirada: lo que quedó en la cola no se usa
        if vetado(t):
            continue        # anuncio pagado o promoción
        base = bases.get(t["author"], 1.0)
        fuera.append((score(t, base, ahora), t))
    fuera.sort(key=lambda p: (p[0], engagement(p[1])), reverse=True)
    return fuera


def rank_por_ventana(queue, skip_ids, ahora=None, ventanas=None):
    """Devuelve (candidatos ordenados, ventana usada en horas).

    Gana la ventana MÁS ESTRECHA que tenga material. Si al momento de
    publicar hay algo bueno de la última hora, sale eso; si no hay nada que
    cumpla, se abre a 2 horas, luego a 4, y así.

    CON UNA SALVEDAD. Si la siguiente ventana trae algo mucho mejor
    (FACTOR_RESCATE veces más), se cede y sale ese. Sin esta regla, medido
    sobre la cola real, 1 de cada 4 publicaciones salía con menos de la
    mitad del engagement de algo que estaba a una hora de distancia; el peor
    caso fue 194 contra 9,149. Lo más fresco y lo que más probabilidad de
    éxito tiene no siempre son el mismo tweet, y cuando la diferencia es
    enorme vale más la pena el que va a funcionar.

    El rescate mira UNA ventana más atrás, no las 24 horas completas. Si
    mirara todo el rango acabaría publicando siempre lo mejor del día, con
    4.9 h de antigüedad promedio, y dejaría de ser contenido del momento.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    ventanas = ventanas or config.VENTANAS_HORAS
    bases = baselines(queue, ahora)

    fresco = None          # (candidatos, horas) de la ventana estrecha que ganó
    for horas in ventanas:
        candidatos = _elegibles(queue, skip_ids, ahora, horas, bases)
        if not candidatos:
            continue
        if fresco is None:
            fresco = (candidatos, horas)
            continue
        # Cada ventana contiene a la anterior, así que aquí ya solo se
        # compara el mejor de las dos. Solo se cede si la diferencia es
        # grande; si no, se queda lo fresco.
        factor = getattr(config, "FACTOR_RESCATE", 0) or 0
        if factor and candidatos[0][0] >= fresco[0][0][0] * factor:
            return candidatos, horas
        return fresco
    return fresco if fresco else ([], None)


# Compatibilidad con el código anterior
def rank_eligible(queue, skip_ids, now=None):
    candidatos, _ = rank_por_ventana(queue, skip_ids, now)
    return candidatos
