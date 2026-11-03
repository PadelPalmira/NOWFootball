"""Diagnóstico: muestra tal cual lo que devuelve twitterapi.io.

Úsalo la primera vez (y si algo deja de funcionar) para confirmar que los
nombres de los campos siguen siendo los que el bot espera.

    python -m bot.probe NFL_Stats
"""
import json
import sys

import requests

from . import config, xsource


def run(username):
    r = requests.get(
        f"{xsource.BASE}/twitter/user/last_tweets",
        params={"userName": username},
        headers={"X-API-Key": config.TWITTERAPI_KEY},
        timeout=45,
    )
    print(f"HTTP {r.status_code}\n")
    payload = r.json()

    data = payload.get("data") or payload
    tweets = data.get("tweets") if isinstance(data, dict) else data
    if not tweets:
        print("Sin tweets. Respuesta completa:")
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:3000])
        return 1

    print("--- PRIMER TWEET EN CRUDO ---")
    print(json.dumps(tweets[0], indent=2, ensure_ascii=False)[:3000])

    print("\n--- LO QUE EL BOT LOGRA EXTRAER ---")
    parsed = xsource.fetch_account(username)
    print(f"{len(parsed)} de {len(tweets)} tweets tienen foto y son originales\n")
    for t in parsed[:5]:
        print(f"  {t['retweets']:>6} RT | {t['created_at'][:16]} | {t['text'][:60]!r}")
        print(f"         {t['image_url'][:95]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1] if len(sys.argv) > 1 else config.ACCOUNTS[0]))
