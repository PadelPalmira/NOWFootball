"""Puntuación de candidatos.

El problema: @NFL_Stats tiene muchísimo más alcance que @polymarketblitz.
Comparar reposts en crudo haría que la cuenta chica nunca ganara.
Solución: normalizar contra la mediana de reposts de la propia cuenta,
así compite "qué tan por encima de su propio promedio está cada post".
"""
import datetime as dt
import statistics

from . import config


def age_hours(tweet, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    created = dt.datetime.fromisoformat(tweet["created_at"])
    return (now - created).total_seconds() / 3600.0


def decay_for(hours):
    for limit, factor in config.DECAY:
        if hours < limit:
            return factor
    return config.DECAY[-1][1]


def baselines(queue):
    """Mediana de reposts por cuenta, sobre lo que haya en la cola."""
    buckets = {}
    for t in queue.values():
        buckets.setdefault(t["author"], []).append(t.get("retweets", 0))
    return {a: max(statistics.median(v), 1) for a, v in buckets.items() if v}


def score(tweet, base, now=None):
    hours = age_hours(tweet, now)
    relative = tweet.get("retweets", 0) / max(base, 1)
    return relative * decay_for(hours)


def rank_eligible(queue, skip_ids, now=None):
    """Devuelve los candidatos elegibles ordenados de mejor a peor."""
    now = now or dt.datetime.now(dt.timezone.utc)
    bases = baselines(queue)
    out = []
    for tid, t in queue.items():
        if tid in skip_ids:
            continue
        hours = age_hours(t, now)
        if hours < config.MATURITY_HOURS:
            continue                      # todavía no madura: no sabemos si es buena
        if hours > config.MAX_QUEUE_AGE_DAYS * 24:
            continue
        if t.get("retweets", 0) < config.MIN_RETWEETS:
            continue
        base = bases.get(t["author"], 1)
        out.append((score(t, base, now), t))
    out.sort(key=lambda p: (p[0], p[1].get("retweets", 0)), reverse=True)
    return out
