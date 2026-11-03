"""Revision completa del sistema, en español y sin tecnicismos.

Esto es lo que corre el boton "1. Revisar que todo este bien" en GitHub.
Comprueba las tres llaves, el logo y el estado de la cola, y al final dice
en una linea si se puede publicar o que falta.
"""
import os
import sys

import requests

from . import config, store

OK, MAL, AVISO = "[OK]   ", "[ERROR]", "[AVISO]"
problemas = []
avisos = []


def seccion(titulo):
    print(f"\n{'=' * 60}\n{titulo}\n{'=' * 60}")


def revisar_x():
    seccion("1. CONEXION CON X (twitterapi.io)")
    if not config.TWITTERAPI_KEY:
        print(f"{MAL} Falta la llave TWITTERAPI_KEY.")
        print("        Ve a Settings > Secrets and variables > Actions")
        print("        y crea el secret llamado TWITTERAPI_KEY.")
        problemas.append("Falta la llave de twitterapi.io")
        return

    total_fotos = 0
    for cuenta in config.ACCOUNTS:
        try:
            from . import xsource
            tweets = xsource.fetch_account(cuenta)
            total_fotos += len(tweets)
            if tweets:
                print(f"{OK} @{cuenta}: {len(tweets)} publicaciones con imagen")
            else:
                print(f"{AVISO} @{cuenta}: conecta bien, pero no encontro imagenes ahora mismo")
                avisos.append(f"@{cuenta} sin imagenes en este momento")
        except requests.HTTPError as e:
            codigo = e.response.status_code if e.response is not None else "?"
            if codigo == 401:
                print(f"{MAL} @{cuenta}: la llave de twitterapi.io es incorrecta.")
                problemas.append("La llave de twitterapi.io no sirve")
                return          # la llave es la misma para todas: no tiene caso seguir
            if codigo == 402:
                print(f"{MAL} @{cuenta}: se acabo el saldo de twitterapi.io. Recarga en su pagina.")
                problemas.append("Sin saldo en twitterapi.io")
                return
            if codigo == 404:
                print(f"{MAL} @{cuenta}: esa cuenta no existe o cambio de nombre en X.")
                print("        Revisa como se escribe en ACCOUNTS, dentro de bot/config.py.")
                problemas.append(f"@{cuenta} no existe en X")
            elif codigo == 429:
                print(f"{MAL} @{cuenta}: twitterapi.io sigue pidiendo esperar (429),")
                print("        incluso despues de varios reintentos. Vuelve a correr")
                print("        este boton en unos minutos.")
                problemas.append(f"twitterapi.io pidio esperar en @{cuenta}")
            else:
                print(f"{MAL} @{cuenta}: error {codigo} al consultar.")
                problemas.append(f"Error {codigo} consultando @{cuenta}")
            continue            # seguimos con las demas cuentas
        except Exception as e:
            print(f"{MAL} @{cuenta}: {e}")
            problemas.append(f"Fallo consultando @{cuenta}")
            continue

    if total_fotos == 0 and not problemas:
        print(f"\n{MAL} Ninguna cuenta devolvio imagenes.")
        print("        Esto casi siempre significa que twitterapi.io cambio algo")
        print("        por dentro. Mandale esta pantalla a Claude y lo ajusta.")
        problemas.append("Ninguna cuenta devolvio imagenes")


def revisar_facebook():
    seccion("2. CONEXION CON FACEBOOK")
    if not config.FB_PAGE_TOKEN or not config.FB_PAGE_ID:
        faltan = []
        if not config.FB_PAGE_ID:
            faltan.append("FB_PAGE_ID")
        if not config.FB_PAGE_TOKEN:
            faltan.append("FB_PAGE_TOKEN")
        print(f"{MAL} Faltan estos secrets: {', '.join(faltan)}")
        problemas.append("Faltan datos de Facebook")
        return

    try:
        r = requests.get(
            f"https://graph.facebook.com/{config.FB_API_VERSION}/{config.FB_PAGE_ID}",
            params={"fields": "name,fan_count", "access_token": config.FB_PAGE_TOKEN},
            timeout=30,
        )
        datos = r.json()
    except Exception as e:
        print(f"{MAL} No se pudo contactar a Facebook: {e}")
        problemas.append("No se pudo contactar a Facebook")
        return

    if "error" in datos:
        err = datos["error"]
        codigo = err.get("code")
        print(f"{MAL} Facebook rechazo la conexion: {err.get('message')}")
        if codigo == 190:
            print("        El token vencio o se invalido (pasa si cambiaste tu")
            print("        contrasena de Facebook). Hay que sacar uno nuevo:")
            print("        repite el Paso 4 de la guia.")
        problemas.append("El token de Facebook no sirve")
        return

    print(f"{OK} Conectado a la pagina: {datos.get('name')}")
    if datos.get("fan_count") is not None:
        print(f"       Seguidores: {datos['fan_count']:,}")

    # Permiso de publicacion
    try:
        p = requests.get(
            f"https://graph.facebook.com/{config.FB_API_VERSION}/me/permissions",
            params={"access_token": config.FB_PAGE_TOKEN}, timeout=30,
        ).json()
        otorgados = {x["permission"] for x in p.get("data", []) if x.get("status") == "granted"}
        if "pages_manage_posts" in otorgados:
            print(f"{OK} Tiene permiso para publicar")
        elif otorgados:
            print(f"{AVISO} No veo el permiso 'pages_manage_posts'.")
            print("        Si la publicacion de prueba falla, repite el Paso 4.")
            avisos.append("Permiso de publicacion no confirmado")
    except Exception:
        pass


def revisar_logo():
    seccion("3. LOGO")
    if os.path.exists(config.LOGO_PATH):
        try:
            from PIL import Image
            im = Image.open(config.LOGO_PATH)
            print(f"{OK} Logo encontrado ({im.size[0]}x{im.size[1]} pixeles)")
            if im.mode != "RGBA":
                print(f"{AVISO} El logo no tiene fondo transparente.")
                print("        Se vera con un recuadro solido encima de la imagen.")
                avisos.append("El logo no es transparente")
        except Exception:
            print(f"{MAL} El archivo del logo existe pero esta danado.")
            problemas.append("El logo no se puede abrir")
    else:
        print(f"{AVISO} No hay logo en assets/logo.png")
        print("        El bot va a publicar igual, pero sin tu logo en la imagen.")
        avisos.append("Sin logo")


def revisar_cola():
    seccion("4. COLA DE CONTENIDO")
    import datetime as dt
    from . import scoring

    cola = store.load_queue()
    publicados = store.load_posted()
    ya_usados = store.posted_ids(publicados)
    reales = [i for i in publicados.get("items", []) if not i.get("skipped")]

    print(f"       Candidatos guardados : {len(cola)}")
    print(f"       Ya publicados        : {len(reales)}")

    if not cola:
        print(f"\n{AVISO} La cola esta vacia.")
        print("        Es normal si apenas instalaste. Corre el boton")
        print("        '2. Buscar contenido nuevo' para llenarla.")
        avisos.append("Cola vacia")
        return

    listos = scoring.rank_eligible(cola, ya_usados)
    ahora = dt.datetime.now(dt.timezone.utc)
    inmaduros = sum(1 for t in cola.values()
                    if scoring.age_hours(t, ahora) < config.MATURITY_HOURS
                    and t["id"] not in ya_usados)

    print(f"       Listos para publicar : {len(listos)}")
    print(f"       Aun madurando        : {inmaduros} (esperan {config.MATURITY_HOURS}h)")

    if listos:
        print(f"\n{OK} Lo siguiente que publicaria:")
        for sc, t in listos[:3]:
            print(f"       @{t['author']:<18} {t['retweets']:>6} reposts")
    else:
        print(f"\n{AVISO} Ahorita no hay nada listo para publicar.")
        if inmaduros:
            print(f"        Hay {inmaduros} esperando a cumplir {config.MATURITY_HOURS} horas.")
            print("        Vuelve a revisar mas tarde: es el comportamiento correcto.")
        else:
            print(f"        Nada alcanza el minimo de {config.MIN_RETWEETS} reposts.")
        avisos.append("Nada listo para publicar en este momento")


def run():
    print("\n" + "#" * 60)
    print("#  REVISION DEL BOT DE NOW FOOTBALL")
    print("#" * 60)
    print(f"\nCuentas que sigue: {', '.join('@' + a for a in config.ACCOUNTS)}")

    revisar_x()
    revisar_facebook()
    revisar_logo()
    revisar_cola()

    seccion("RESULTADO")
    if problemas:
        print("HAY QUE ARREGLAR ESTO ANTES DE PUBLICAR:\n")
        for p in problemas:
            print(f"   - {p}")
        if avisos:
            print("\nAdemas, cosas menores:")
            for a in avisos:
                print(f"   - {a}")
        print("\nSi no sabes que hacer con algo de esto, copia esta pantalla")
        print("completa y mandasela a Claude.")
        return 1

    print("TODO ESTA BIEN. El bot puede publicar.\n")
    if avisos:
        print("Notas (nada grave):")
        for a in avisos:
            print(f"   - {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
