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


def run(dry_run=False, ahora=None, rng=None):
    queue = store.load_queue()
    posted = store.load_posted()
    usados = store.posted_ids(posted)
    bloqueados = _cargar_bloqueados()
    rng = rng or random
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    sin_datos_frescos = False

    # ---------- Frenos de ritmo (no aplican a la prueba sin publicar)
    if not dry_run:
        adelante, razon, momento = ritmo.decidir(posted, ahora, rng)
        print(f"Ritmo: {razon}\n")
        if not adelante:
            return 0
    else:
        momento = ritmo.momento_objetivo(ahora, rng)

    # ---------- Datos frescos de X
    # Se consulta justo ahora, no se usa lo que hubiera guardado de antes:
    # buscamos lo mejor de las últimas 2 horas y eso cambia minuto a minuto.
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

    # ---------- Elegir candidato: ventana más reciente que tenga algo
    ranking, ventana = scoring.rank_por_ventana(queue, usados, ahora)
    if not ranking:
        print(f"Nada publicable en las últimas {config.VENTANAS_HORAS[-1]} horas.")
        print("Puede ser que las cuentas no hayan publicado imágenes nuevas,")
        print("o que todo lo reciente ya se haya publicado antes.")
        if sin_datos_frescos:
            print("\nOJO: además X no respondió en esta corrida.", file=sys.stderr)
            return 1
        return 0
    print(f"Ventana usada: últimas {ventana} h · {len(ranking)} candidatos")
    if ventana != config.VENTANAS_HORAS[0]:
        print(f"  (no había nada en las últimas {config.VENTANAS_HORAS[0]} h, "
              f"se amplió la búsqueda)")

    anterior = _ultima_cuenta(posted)
    if config.NO_REPETIR_CUENTA_SEGUIDA and anterior and len(ranking) > 1:
        otras = [(s, t) for s, t in ranking if t["author"] != anterior]
        if otras:
            ranking = otras + [(s, t) for s, t in ranking if t["author"] == anterior]
            print(f"El post anterior fue de @{anterior}; se prefiere otra cuenta.\n")

    print("\nProbando los mejores:\n")
    tmpdir = tempfile.mkdtemp(prefix="nfb_")

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
            _, original = imaging.build(tweet["image_url"], destino)
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

        texto = caption.build(tweet, rng)

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
            return 0

        try:
            resp = facebook.post_photo(destino, texto, publicar_en=momento)
        except Exception as e:
            posted["fallos_seguidos"] = ritmo.fallos_seguidos(posted) + 1
            store.save_posted(posted)
            print(f"    [!] Falló la publicación: {e}", file=sys.stderr)
            print(f"    Fallos seguidos: {posted['fallos_seguidos']} de "
                  f"{config.MAX_FALLOS_SEGUIDOS}", file=sys.stderr)
            return 1

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
        store.save_posted(posted)

        if resp.get("modo") == "programado":
            local = momento.astimezone(config.TZ)
            print(f"\n✅ PROGRAMADO para el {local.strftime('%d/%m a las %H:%M')} "
                  f"(hora de Mazatlán) · {etiqueta}")
            print("   Puedes revisarlo o cancelarlo en Meta Business Suite,")
            print("   en la sección de publicaciones programadas.")
        else:
            print(f"\n✅ Publicado en Now Football ({etiqueta})")
        print(f"   ID de Facebook: {resp.get('post_id')}")
        return 0

    store.save_posted(posted)
    print("Probé los mejores candidatos y ninguno sirvió en esta corrida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(dry_run="--dry-run" in sys.argv))
