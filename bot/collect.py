"""Recolector: trae tweets recientes con imagen y los mete/actualiza en la cola.

Corre cada 4h. No publica nada. Su trabajo es juntar candidatos y mantener
actualizado el conteo de reposts de los que ya están en la cola.
"""
import datetime as dt
import sys

from . import config, store, xsource


def run():
    queue = store.load_queue()
    now = dt.datetime.now(dt.timezone.utc)
    nuevos, actualizados, errores = 0, 0, []

    for account in config.ACCOUNTS:
        try:
            tweets = xsource.fetch_account(account)
        except Exception as e:
            errores.append(f"{account}: {e}")
            print(f"  [!] {account}: {e}")
            continue

        for t in tweets:
            tid = t["id"]
            if tid in queue:
                # Solo refrescamos métricas; lo demás no cambia
                queue[tid]["retweets"] = max(queue[tid].get("retweets", 0), t["retweets"])
                queue[tid]["likes"] = max(queue[tid].get("likes", 0), t["likes"])
                queue[tid]["last_seen"] = now.isoformat()
                actualizados += 1
            else:
                t["first_seen"] = now.isoformat()
                t["last_seen"] = now.isoformat()
                queue[tid] = t
                nuevos += 1
        print(f"  {account}: {len(tweets)} tweets con imagen")

    # Limpieza: fuera lo demasiado viejo
    corte = now - dt.timedelta(days=config.MAX_QUEUE_AGE_DAYS)
    antes = len(queue)
    queue = {
        k: v for k, v in queue.items()
        if dt.datetime.fromisoformat(v["created_at"]) > corte
    }

    # Tope duro por si acaso: conservamos los más recientes
    if len(queue) > config.QUEUE_HARD_LIMIT:
        ordenados = sorted(queue.items(), key=lambda kv: kv[1]["created_at"], reverse=True)
        queue = dict(ordenados[: config.QUEUE_HARD_LIMIT])

    store.save_queue(queue)
    print(f"\nCola: {len(queue)} candidatos "
          f"(+{nuevos} nuevos, {actualizados} actualizados, -{antes - len(queue)} purgados)")

    if errores and len(errores) == len(config.ACCOUNTS):
        print("Todas las cuentas fallaron.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
