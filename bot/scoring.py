"""Elige qué publicar: lo más caliente de la ventana de tiempo más reciente.

Dos ideas sostienen esto:

1. VENTANAS. Al momento de publicar se mira solo lo de las últimas 2 horas.
   Si ahí no hay nada que sirva, se abre a 4 horas, luego a 8, luego a 24.
   La primera ventana con material gana, así que lo que sale siempre es lo
   más fresco disponible.

2. TASA, no total. Dentro de una ventana de 2 horas, comparar reposts en
   crudo favorece al tweet más viejo: uno de hace 110 minutos tuvo cinco
   veces más tiempo de acumular que uno de hace 20. Por eso se mide
   reposts POR HORA. Y como @NFL_Stats tiene mucho más alcance que
   @polymarketblitz, esa tasa se compara contra la tasa típica de su propia
   cuenta, para que la cuenta grande no gane siempre.
"""
import datetime as dt
import statistics

from . import config


def age_hours(tweet, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    created = dt.datetime.fromisoformat(tweet["created_at"])
    return (now - created).total_seconds() / 3600.0


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
    """Qué tan por encima de lo normal para su cuenta está este tweet."""
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
        base = bases.get(t["author"], 1.0)
        fuera.append((score(t, base, ahora), t))
    fuera.sort(key=lambda p: (p[0], engagement(p[1])), reverse=True)
    return fuera


def rank_por_ventana(queue, skip_ids, ahora=None, ventanas=None):
    """Devuelve (candidatos ordenados, ventana usada en horas).

    Prueba las ventanas en orden y se queda con la primera que tenga algo.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    ventanas = ventanas or config.VENTANAS_HORAS
    bases = baselines(queue, ahora)
    for horas in ventanas:
        candidatos = _elegibles(queue, skip_ids, ahora, horas, bases)
        if candidatos:
            return candidatos, horas
    return [], None


# Compatibilidad con el código anterior
def rank_eligible(queue, skip_ids, now=None):
    candidatos, _ = rank_por_ventana(queue, skip_ids, now)
    return candidatos
