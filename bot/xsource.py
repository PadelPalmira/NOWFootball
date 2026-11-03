"""Cliente de twitterapi.io: trae los tweets recientes de una cuenta y los normaliza.

Escrito a la defensiva: los proveedores terceros cambian nombres de campos sin avisar,
así que cada dato se busca en varias rutas posibles antes de rendirse.
"""
import datetime as dt
import html
import random
import time

import requests

from . import config

BASE = "https://api.twitterapi.io"

# twitterapi.io limita cuántas peticiones seguidas acepta. Si se le piden las
# tres cuentas de golpe contesta 429 ("demasiadas peticiones"), así que aquí se
# espacian las llamadas y se reintenta con esperas cada vez más largas.
PAUSA_ENTRE_LLAMADAS = 2.0          # segundos mínimos entre una petición y la siguiente
INTENTOS = 4
REINTENTABLES = (429, 500, 502, 503, 504)

_ultima_llamada = [0.0]


def _pedir(url, params, headers, timeout=45):
    espera = 3.0
    for intento in range(1, INTENTOS + 1):
        transcurrido = time.monotonic() - _ultima_llamada[0]
        if transcurrido < PAUSA_ENTRE_LLAMADAS:
            time.sleep(PAUSA_ENTRE_LLAMADAS - transcurrido)
        _ultima_llamada[0] = time.monotonic()

        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code not in REINTENTABLES:
            r.raise_for_status()
            return r
        if intento == INTENTOS:
            r.raise_for_status()

        # Respetamos Retry-After si el servidor lo manda
        cabecera = (r.headers.get("Retry-After") or "").strip()
        pausa = float(cabecera) if cabecera.isdigit() else espera
        pausa = min(pausa, 30.0) + random.uniform(0, 1.0)
        print(f"    (respuesta {r.status_code}; reintento {intento} de "
              f"{INTENTOS - 1} en {pausa:.0f}s)")
        time.sleep(pausa)
        espera *= 2
    raise RuntimeError("inalcanzable")


def _first(d, *keys, default=None):
    """Devuelve el primer valor no vacío entre varias llaves posibles."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, "", []):
            return d[k]
    return default


def _parse_date(raw):
    """twitterapi.io suele devolver formato Twitter clásico; aceptamos varios."""
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        return dt.datetime.fromtimestamp(raw, tz=dt.timezone.utc)
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            d = dt.datetime.strptime(raw, fmt)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _extract_photos(tweet):
    """Saca las URLs de foto. Ignora video y GIF: queremos imagen fija."""
    urls = []
    for container in ("extendedEntities", "extended_entities", "entities"):
        ent = tweet.get(container) or {}
        for m in (ent.get("media") or []):
            if (m.get("type") or "").lower() != "photo":
                continue
            u = _first(m, "media_url_https", "media_url", "url")
            if u:
                urls.append(u)
        if urls:
            break
    # Algunos proveedores exponen un arreglo plano
    if not urls:
        for key in ("mediaUrls", "media_urls", "photos", "images"):
            vals = tweet.get(key) or []
            for v in vals:
                if isinstance(v, str):
                    urls.append(v)
                elif isinstance(v, dict):
                    u = _first(v, "url", "media_url_https", "media_url")
                    if u:
                        urls.append(u)
            if urls:
                break
    # Pedimos la versión grande
    out = []
    for u in urls:
        if "twimg.com" in u and "name=" not in u:
            u = u + ("&" if "?" in u else "?") + "format=jpg&name=large"
        out.append(u)
    return out


def _is_retweet(tweet):
    if tweet.get("retweeted_tweet") or tweet.get("retweetedTweet"):
        return True
    txt = (tweet.get("text") or "")
    return txt.startswith("RT @")


def _is_reply(tweet):
    return bool(_first(tweet, "isReply", "is_reply", default=False)) or bool(
        _first(tweet, "inReplyToId", "in_reply_to_id", "in_reply_to_status_id")
    )


def fetch_account(username, api_key=None, limit=None):
    """Devuelve una lista de tweets normalizados, solo los que traen foto."""
    api_key = api_key or config.TWITTERAPI_KEY
    limit = limit or config.TWEETS_PER_ACCOUNT
    if not api_key:
        raise RuntimeError("Falta TWITTERAPI_KEY")

    r = _pedir(
        f"{BASE}/twitter/user/last_tweets",
        params={"userName": username},
        headers={"X-API-Key": api_key},
    )
    payload = r.json()

    data = payload.get("data") or payload
    raw_tweets = (
        data.get("tweets")
        if isinstance(data, dict) and isinstance(data.get("tweets"), list)
        else (data if isinstance(data, list) else [])
    )

    results = []
    for t in raw_tweets[:limit]:
        if _is_retweet(t) or _is_reply(t):
            continue
        photos = _extract_photos(t)
        if not photos:
            continue
        created = _parse_date(_first(t, "createdAt", "created_at", "date"))
        if not created:
            continue
        tid = str(_first(t, "id", "id_str", "tweet_id", default=""))
        if not tid:
            continue
        results.append({
            "id": tid,
            "author": username,
            "text": html.unescape(t.get("text") or ""),
            "image_url": photos[0],
            "url": _first(t, "url", "twitterUrl", default=f"https://x.com/{username}/status/{tid}"),
            "created_at": created.isoformat(),
            "retweets": int(_first(t, "retweetCount", "retweet_count", default=0) or 0),
            "likes": int(_first(t, "likeCount", "favorite_count", "like_count", default=0) or 0),
            "quotes": int(_first(t, "quoteCount", "quote_count", default=0) or 0),
        })
    return results
