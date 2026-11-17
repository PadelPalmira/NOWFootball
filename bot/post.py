"""Publicador: elige el mejor candidato y lo publica (o lo deja programado).

Antes de publicar pasa por todos los frenos de bot/ritmo.py: pausa manual,
cupo del día, arranque gradual, separación mínima, ventana horaria y el
reparto aleatorio de turnos.
"""
import datetime as dt
import json
import os
import random
import shutil
import sys
import tempfile

from . import caption, collect, config, facebook, imaging, phash, ritmo, scoring, store

MAX_INTENTOS = 6     # cuántos candidatos probar antes de rendirse en esta corrida


def _cargar_bloqueados():
    """Cuentas o publicaciones que el bot nunca debe usar."""
    if not os.path.exists(config.BLOQUEADOS_FILE):
        return {"cuentas": [], "tweets": []}
    try:
        with open(config.BLOQUEADOS_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"cuentas": [], "tweets": []}
    return {"cuentas": [str(c).lstrip("@").lower() for c in d.get("cuentas", [])],
            "tweets": [str(t) for t in d.get("tweets", [])]}


def _es_duplicada(ph, url, posted):
    """Dos filtros: URL exacta del medio (certeza) y similitud visual."""
    for item in posted.get("items", []):
        if url and item.get("image_url") == url:
            return True
        vh = item.get("phash")
        if vh and phash.distance(ph, vh) <= config.PHASH_DISTANCE:
            return True
    return False


def _ultima_cuenta(posted):
    for item in reversed(posted.get("items", [])):
        if not item.get("skipped"):
            return item.get("author")
    return None


def _intentar_una(queue, posted, usados, bloqueados, momento, ahora, rng,
                  tmpdir, dry_run):
    """Elige el mejor candidato y lo publica o lo deja programado.

    Devuelve uno de: "ok", "nada", "prueba", "fallo".
    """
    ranking, ventana = scoring.rank_por_ventana(queue, usados, ahora)
    if not ranking:
        return "nada"

    print(f"Ventana usada: últimas {ventana} h · {len(ranking)} candidatos")
    if ventana != config.VENTANAS_HORAS[0]:
        print(f"  (no había nada en las últimas {config.VENTANAS_HORAS[0]} h, "
              f"se amplió la búsqueda)")

    anterior = _ultima_cuenta(posted)
    if config.NO_REPETIR_CUENTA_SEGUIDA and anterior and len(ranking) > 1:
        otras = [(s, t) for s, t in ranking if t["author"] != anterior]
        if otras:
            ranking = otras + [(s, t) for s, t in ranking if t["author"] == anterior]
            print(f"La anterior fue de @{anterior}; se prefiere otra cuenta.")

    print("\nProbando los mejores:\n")

    for score, tweet in ranking[:MAX_INTENTOS]:
        horas = scoring.age_hours(tweet, ahora)
        etiqueta = (f"@{tweet['author']} · {tweet['retweets']} RT en "
                    f"{horas:.1f} h ({scoring.tasa(tweet, ahora):.0f} RT/h) "
                    f"· score {score:.2f}")
        print(f"  → {etiqueta}")

        if tweet["author"].lower() in bloqueados["cuentas"]:
            print("    [x] Cuenta en la lista negra. Se omite.")
            continue
        if tweet["id"] in bloqueados["tweets"]:
            print("    [x] Publicación en la lista negra. Se omite.")
            continue

        destino = os.path.join(tmpdir, f"{tweet['id']}.jpg")
        try:
            _, original = imaging.build(tweet["image_url"], destino,
                                        texto=tweet.get("text"),
                                        autor=tweet.get("author"), verboso=True)
        except Exception as e:
            print(f"    [!] No se pudo procesar la imagen: {e}")
            continue

        ph = phash.phash(original)
        if _es_duplicada(ph, tweet.get("image_url"), posted):
            print("    [=] Imagen ya publicada antes. La marco como usada y sigo.")
            posted["items"].append({
                "id": tweet["id"], "author": tweet["author"],
                "phash": ph, "image_url": tweet.get("image_url"),
                "skipped": "duplicada",
                "at": ahora.isoformat(),
            })
            usados.add(tweet["id"])
            continue

        texto = caption.build(tweet, rng, verboso=True)

        if dry_run:
            os.makedirs("preview", exist_ok=True)
            shutil.copy(destino, "preview/siguiente.jpg")
            with open("preview/caption.txt", "w", encoding="utf-8") as fh:
                fh.write(texto)
            cuando = (momento.astimezone(config.TZ).strftime("%d/%m a las %H:%M")
                      if momento else "de inmediato")
            with open("preview/resumen.md", "w", encoding="utf-8") as fh:
                fh.write(
                    "## Esto es lo que se publicaria\n\n"
                    f"- **Cuenta de origen:** @{tweet['author']}\n"
                    f"- **Reposts que tiene:** {tweet['retweets']} "
                    f"en {horas:.1f} h ({scoring.tasa(tweet, ahora):.0f} por hora)\n"
                    f"- **Ventana:** lo mejor de las ultimas {ventana} h\n"
                    f"- **Saldria:** {cuando} (hora de Mazatlan)\n"
                    f"- **Publicacion original:** {tweet.get('url')}\n\n"
                    "### Texto que llevaria\n\n"
                    f"```\n{texto}\n```\n\n"
                    "La imagen ya convertida a 4:5 esta como archivo descargable\n"
                    "al final de esta pagina, en la seccion **Artifacts**.\n"
                )
            print("\n--- PRUEBA: no se publicó nada en Facebook ---")
            print(f"Saldría: {cuando}")
            print(f"Texto que llevaría:\n{texto}\n")
            return "prueba"

        try:
            resp = facebook.post_photo(destino, texto, publicar_en=momento)
        except Exception as e:
            posted["fallos_seguidos"] = ritmo.fallos_seguidos(posted) + 1
            store.save_posted(posted)
            print(f"    [!] Falló la publicación: {e}", file=sys.stderr)
            print(f"    Fallos seguidos: {posted['fallos_seguidos']} de "
                  f"{config.MAX_FALLOS_SEGUIDOS}", file=sys.stderr)
            return "fallo"

        posted["fallos_seguidos"] = 0
        posted["items"].append({
            "id": tweet["id"],
            "author": tweet["author"],
            "phash": ph,
            "image_url": tweet.get("image_url"),
            "retweets": tweet["retweets"],
            "score": round(score, 3),
            "tweet_url": tweet.get("url"),
            "fb_post_id": resp.get("post_id"),
            "modo": resp.get("modo"),
            "ventana_h": ventana,
            "tasa": round(scoring.tasa(tweet, ahora), 1),
            "publica_en": resp.get("publica_en"),
            "at": ahora.isoformat(),
        })
        usados.add(tweet["id"])
        store.save_posted(posted)

        if resp.get("modo") == "programado":
            local = momento.astimezone(config.TZ)
            print(f"\n✅ PROGRAMADO para el {local.strftime('%d/%m a las %H:%M')} "
                  f"(hora de Mazatlán) · {etiqueta}")
        else:
            print(f"\n✅ Publicado en Now Football ({etiqueta})")
        print(f"   ID de Facebook: {resp.get('post_id')}")
        return "ok"

    return "nada"


def run(dry_run=False, ahora=None, rng=None):
    """Una despertada del bot.

    Desde la v1.18 una despertada puede dejar VARIAS publicaciones
    programadas, no una. El motivo está medido: el reloj de GitHub solo
    despierta al bot dos o tres veces al día y además las despertadas llegan
    pegadas. El 12 de noviembre llegaron tres en cinco minutos; la primera
    publicó y las otras dos murieron en el freno de separación mínima. Ese
    día salió UNA publicación de diez.

    Como no se puede controlar cuándo despierta GitHub, cada despertada deja
    programado lo que quepa dentro de HORIZONTE_HORAS, separado como debe
    ser. El programador de Facebook sí es puntual.
    """
    queue = store.load_queue()
    posted = store.load_posted()
    usados = store.posted_ids(posted)
    bloqueados = _cargar_bloqueados()
    rng = rng or random
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    sin_datos_frescos = False

    # ---------- Freno de ritmo, antes de gastar una sola llamada a X
    if not dry_run:
        adelante, razon, momento = ritmo.decidir(posted, ahora, rng)
        print(f"Ritmo: {razon}\n")
        if not adelante:
            return 0
    else:
        momento = ritmo.momento_objetivo(ahora, rng, posted)

    # ---------- Datos frescos de X
    # Se consulta justo ahora, no se usa lo que hubiera guardado de antes:
    # buscamos lo mejor de la última hora y eso cambia minuto a minuto.
    if not dry_run or config.REFRESCAR_EN_PRUEBA:
        print("Consultando X...")
        queue, nuevos, _, errores = collect.refrescar(queue, ahora)
        queue = collect.limpiar(queue, ahora)
        store.save_queue(queue)
        if errores:
            fallidas = ", ".join("@" + c for c, _ in errores)
            print(f"  [!] No respondieron: {fallidas}")
        sin_datos_frescos = len(errores) == len(config.ACCOUNTS)
        if sin_datos_frescos:
            print("  [!] Ninguna cuenta de X respondió. Se intenta con lo que ya")
            print("      estaba guardado, que puede tener los números algo atrasados.")
        print(f"  {nuevos} publicaciones nuevas · {len(queue)} en total\n")

    tmpdir = tempfile.mkdtemp(prefix="nfb_")
    tope = max(int(getattr(config, "MAX_POR_CORRIDA", 1)), 1)
    hechas = 0

    while True:
        estado = _intentar_una(queue, posted, usados, bloqueados, momento,
                               ahora, rng, tmpdir, dry_run)

        if estado == "prueba":
            return 0
        if estado == "fallo":
            return 1
        if estado == "nada":
            if hechas == 0:
                print(f"Nada publicable en las últimas "
                      f"{config.VENTANAS_HORAS[-1]} horas.")
                print("Puede ser que las cuentas no hayan publicado imágenes")
                print("nuevas, o que todo lo reciente ya se haya publicado.")
                store.save_posted(posted)
                if sin_datos_frescos:
                    print("\nOJO: además X no respondió en esta corrida.",
                          file=sys.stderr)
                    return 1
            else:
                print("\nYa no quedan candidatos nuevos para programar otra.")
            break

        hechas += 1
        if hechas >= tope:
            print(f"\nTope de {tope} publicaciones por despertada.")
            break

        # ¿Cabe otra dentro del horizonte? decidir() ya toma en cuenta las que
        # se acaban de programar, así que la coloca después de la última.
        adelante, razon, momento = ritmo.decidir(posted, ahora, rng)
        if not adelante:
            print(f"\nNo cabe otra: {razon}")
            break

    if hechas:
        futuras = [m for m in ritmo.momentos_programados(posted) if m > ahora]
        print(f"\n{'='*58}")
        print(f"Esta despertada dejó {hechas} publicación(es) lista(s).")
        if futuras:
            horas = ", ".join(m.astimezone(config.TZ).strftime("%H:%M")
                              for m in sorted(futuras))
            print(f"Programadas en Facebook para las: {horas} (hora de Mazatlán)")
        print("Puedes revisarlas o cancelarlas en Meta Business Suite,")
        print("en la sección de publicaciones programadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(dry_run="--dry-run" in sys.argv))
