"""Trae publicaciones recientes de X y las guarda en la cola.

Lo usa el botón "2. Buscar contenido nuevo", pero sobre todo lo usa el
publicador justo antes de publicar: como se busca lo mejor de las últimas
2 horas, los datos tienen que ser del momento, no de hace rato.
"""
import datetime as dt
import sys

from . import config, store, xsource


def refrescar(queue, ahora=None, cuentas=None, silencioso=False):
    """Consulta X y mezcla lo nuevo en la cola.

    Devuelve (queue, nuevos, actualizados, errores). Nunca lanza excepción:
    si una cuenta falla, se anota y se sigue con las demás, porque es
    preferible publicar con dos cuentas que no publicar nada.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    cuentas = cuentas or config.ACCOUNTS
    nuevos = actualizados = 0
    errores = []

    for cuenta in cuentas:
        try:
            tweets = xsource.fetch_account(cuenta)
        except Exception as e:
            errores.append((cuenta, str(e)))
            if not silencioso:
                print(f"  [!] @{cuenta}: {e}")
            continue

        for t in tweets:
            tid = t["id"]
            if tid in queue:
                # Solo se refrescan las métricas; lo demás no cambia
                queue[tid]["retweets"] = max(queue[tid].get("retweets", 0), t["retweets"])
                queue[tid]["likes"] = max(queue[tid].get("likes", 0), t["likes"])
                queue[tid]["last_seen"] = ahora.isoformat()
                actualizados += 1
            else:
                t["first_seen"] = ahora.isoformat()
                t["last_seen"] = ahora.isoformat()
                queue[tid] = t
                nuevos += 1
        if not silencioso:
            print(f"  @{cuenta}: {len(tweets)} publicaciones con imagen")

    return queue, nuevos, actualizados, errores


def _cuentas_seguidas():
    return {c.lstrip("@").lower() for c in config.ACCOUNTS}


def _nacimiento(entrada):
    """Fecha de la publicación, o None si la entrada viene mal.

    Antes esto se leía directo con fromisoformat(v["created_at"]). Una sola
    entrada sin fecha, con fecha ilegible o sin zona horaria tiraba la corrida
    completa con un error de Python, y eso dejaba muertos los botones 2 y 4
    hasta que alguien corrigiera el archivo a mano. Ahora una entrada mala
    simplemente se descarta.
    """
    crudo = entrada.get("created_at")
    if not isinstance(crudo, str) or not crudo:
        return None
    try:
        d = dt.datetime.fromisoformat(crudo)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def limpiar(queue, ahora):
    """Saca de la cola lo viejo, lo malformado y lo de cuentas que ya no se siguen.

    Lo de las cuentas importa: quitar una cuenta de ACCOUNTS evita traer más
    suyos, pero lo que ya estaba guardado seguiría siendo publicable durante
    días si no se purga.
    """
    corte = ahora - dt.timedelta(days=config.MAX_QUEUE_AGE_DAYS)
    seguidas = _cuentas_seguidas()

    limpia = {}
    for k, v in queue.items():
        if not isinstance(v, dict):
            continue
        nacio = _nacimiento(v)
        if nacio is None or nacio <= corte:
            continue
        autor = v.get("author")
        if not isinstance(autor, str) or autor.lstrip("@").lower() not in seguidas:
            continue
        if not v.get("image_url"):
            continue
        limpia[k] = v

    if len(limpia) > config.QUEUE_HARD_LIMIT:
        ordenados = sorted(limpia.items(),
                           key=lambda kv: _nacimiento(kv[1]) or dt.datetime.min.replace(
                               tzinfo=dt.timezone.utc),
                           reverse=True)
        limpia = dict(ordenados[: config.QUEUE_HARD_LIMIT])
    return limpia


def run():
    queue = store.load_queue()
    ahora = dt.datetime.now(dt.timezone.utc)
    antes = len(queue)

    queue, nuevos, actualizados, errores = refrescar(queue, ahora)
    queue = limpiar(queue, ahora)
    store.save_queue(queue)

    print(f"\nCola: {len(queue)} candidatos "
          f"(+{nuevos} nuevos, {actualizados} actualizados, "
          f"{max(0, antes + nuevos - len(queue))} purgados por viejos)")

    if errores and len(errores) == len(config.ACCOUNTS):
        print("Todas las cuentas fallaron.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
