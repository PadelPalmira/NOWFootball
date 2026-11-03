"""Publicador: saca el mejor candidato de la cola y lo postea en Now Football.

Corre cada 2h. Nunca repite imagen: compara con hash perceptual contra todo
lo ya publicado, así ni una versión recortada o recomprimida se cuela dos veces.
"""
import datetime as dt
import os
import shutil
import sys
import tempfile

from . import caption, config, facebook, imaging, phash, scoring, store

MAX_INTENTOS = 6     # cuántos candidatos probar antes de rendirse en esta corrida


def _es_duplicada(ph, url, posted):
    """Dos filtros: URL exacta del medio (certeza) y similitud visual (recomprimidas)."""
    for item in posted.get("items", []):
        if url and item.get("image_url") == url:
            return True
        vh = item.get("phash")
        if vh and phash.distance(ph, vh) <= config.PHASH_DISTANCE:
            return True
    return False


def run(dry_run=False):
    queue = store.load_queue()
    posted = store.load_posted()
    usados = store.posted_ids(posted)

    ranking = scoring.rank_eligible(queue, usados)
    if not ranking:
        print("No hay candidatos elegibles en esta corrida. "
              "Puede ser que todo sea muy reciente o no alcance el mínimo de reposts.")
        return 0

    print(f"{len(ranking)} candidatos elegibles. Probando los mejores:\n")
    tmpdir = tempfile.mkdtemp(prefix="nfb_")

    for score, tweet in ranking[:MAX_INTENTOS]:
        etiqueta = f"@{tweet['author']} · {tweet['retweets']} RT · score {score:.2f}"
        print(f"  → {etiqueta}")

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
                "at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })
            usados.add(tweet["id"])
            continue

        texto = caption.build(tweet)

        if dry_run:
            os.makedirs("preview", exist_ok=True)
            shutil.copy(destino, "preview/siguiente.jpg")
            with open("preview/caption.txt", "w", encoding="utf-8") as fh:
                fh.write(texto)
            with open("preview/resumen.md", "w", encoding="utf-8") as fh:
                fh.write(
                    "## Esto es lo que se publicaria\n\n"
                    f"- **Cuenta de origen:** @{tweet['author']}\n"
                    f"- **Reposts que tiene:** {tweet['retweets']}\n"
                    f"- **Publicacion original:** {tweet.get('url')}\n\n"
                    "### Texto que llevaria\n\n"
                    f"```\n{texto}\n```\n\n"
                    "La imagen ya convertida a 4:5 esta como archivo descargable\n"
                    "al final de esta pagina, en la seccion **Artifacts**.\n"
                )
            print("\n--- PRUEBA: no se publico nada en Facebook ---")
            print(f"Texto que llevaria:\n{texto}\n")
            return 0

        try:
            resp = facebook.post_photo(destino, texto)
        except Exception as e:
            print(f"    [!] Falló la publicación: {e}", file=sys.stderr)
            return 1

        posted["items"].append({
            "id": tweet["id"],
            "author": tweet["author"],
            "phash": ph,
            "image_url": tweet.get("image_url"),
            "retweets": tweet["retweets"],
            "score": round(score, 3),
            "tweet_url": tweet.get("url"),
            "fb_post_id": resp.get("post_id") or resp.get("id"),
            "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        store.save_posted(posted)
        print(f"\n✅ Publicado en Now Football ({etiqueta})")
        print(f"   ID de Facebook: {resp.get('post_id') or resp.get('id')}")
        return 0

    store.save_posted(posted)
    print("Probé los mejores candidatos y ninguno sirvió en esta corrida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(dry_run="--dry-run" in sys.argv))
