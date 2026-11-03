"""Configuración central del bot de Now Football."""
import os
from zoneinfo import ZoneInfo

# ---------- Cuentas de X a monitorear ----------
ACCOUNTS = [
    "NFL_Stats",
    "polymarketblitz",
    "SleeperNFL",
]

# ---------- Credenciales (vienen de GitHub Secrets) ----------
TWITTERAPI_KEY = os.environ.get("TWITTERAPI_KEY", "")
FB_PAGE_ID     = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN  = os.environ.get("FB_PAGE_TOKEN", "")
FB_API_VERSION = os.environ.get("FB_API_VERSION", "v23.0")

# ---------- Modo de publicación ----------
# El contenido es breaking news: publicar 24 h después no tendría sentido, así
# que el bot publica de inmediato.
#
# El post se deja programado con un retraso corto y aleatorio. Esto hace dos
# cosas a la vez: desordena la hora (si publicara al instante caería siempre
# en la hora exacta del reloj, que es la firma de un robot) y te deja una
# ventana para cancelarlo en Meta Business Suite si algo no te cuadra.
# Facebook exige un mínimo de 10 minutos para programar.
# Pon (0, 0) si prefieres que salga al instante.
RETRASO_MINUTOS = (15, 35)

# Que el botón "3. Probar sin publicar" también consulte X en vivo, para que
# la vista previa sea de verdad lo que saldría.
REFRESCAR_EN_PRUEBA = True

# ---------- Ritmo (protección contra verse automatizado) ----------
# Horas locales a las que el bot despierta. El código decide en cuáles
# publica de verdad, repartiendo el cupo del día de forma pareja.
SLOTS_LOCALES   = [8, 10, 12, 14, 16, 18, 20, 22]
VENTANA_INICIO  = 8         # no se programa nada antes de esta hora local
VENTANA_FIN     = 23        # ni después de esta
JITTER_MINUTOS  = 25        # desorden aleatorio, para no caer siempre en punto
TOPE_DIARIO     = 6
TOPE_SEMANAL    = 40
MIN_HORAS_ENTRE_POSTS = 1.5

# Arranque gradual: (días desde la primera publicación, tope de ese periodo).
# Pasados los 14 días se usa TOPE_DIARIO. Un salto repentino de ritmo llama
# más la atención que el ritmo en sí.
RAMPA = [(7, 3), (14, 4)]

NO_REPETIR_CUENTA_SEGUIDA = True

# ---------- Frenos de emergencia ----------
# Si existe un archivo con este nombre en el repositorio, el bot no publica
# nada. Crearlo o borrarlo desde GitHub es un clic.
ARCHIVO_PAUSA       = "PAUSA"
BLOQUEADOS_FILE     = "state/bloqueados.json"
MAX_FALLOS_SEGUIDOS = 3     # tras estos fallos de Facebook, el bot se detiene

# ---------- Reglas de selección ----------
TWEETS_PER_ACCOUNT = 20     # cuántos tweets recientes se revisan por cuenta
MAX_QUEUE_AGE_DAYS = 3      # después de esto se descarta de la cola
MIN_RETWEETS       = 5      # piso mínimo para no publicar algo sin ninguna tracción
QUEUE_HARD_LIMIT   = 400    # tope de la cola para que el JSON no crezca sin control

# Al momento de publicar se busca primero en las últimas 2 horas. Si en esa
# ventana no hay nada que sirva (o todo ya se publicó), se abre a 4 horas,
# luego a 8, y así. La primera ventana que tenga algo, gana.
VENTANAS_HORAS = [2, 4, 8, 24]

# Cuántos tweets necesita una cuenta en el tramo de referencia para que su
# mediana signifique algo. Con menos, se usa la mediana general.
MIN_MUESTRA_BASE = 3

# Un tweet de 10 minutos con 200 reposts está explotando más que uno de 2 horas
# con 300, así que se mide la TASA (reposts por hora), no el total. Este piso de
# edad evita que un tweet de 3 minutos dé una tasa absurda.
EDAD_MINIMA_HORAS = 0.5

# ---------- Imagen 4:5 ----------
CANVAS_W, CANVAS_H = 1080, 1350
BG_COLOR     = "#0B1220"    # fondo liso de marca (solo si apagas el desenfoque)
BLUR_BACKDROP   = True      # fondo = la misma imagen ampliada y desenfocada
BLUR_RADIUS     = 55        # qué tan desenfocado
BLUR_DARKEN     = 0.45      # 1.0 = sin oscurecer; más bajo = más contraste con la imagen
BLUR_SATURATION = 0.80      # baja un poco el color del fondo
EDGE_PAD        = 6         # grosor del borde que despega la imagen del fondo
EDGE_COLOR      = "#FFFFFF"
SIDE_MARGIN  = 40
LOGO_PATH    = "assets/logo.png"
LOGO_MAX_H   = 86
LOGO_STRIP_H = 150          # franja inferior reservada para el logo
PHASH_DISTANCE = 6          # umbral conservador: mejor dejar pasar una variante rara
                            # que bloquear para siempre contenido nuevo bueno

# ---------- Caption ----------
# Mandar siempre el mismo bloque de hashtags es una de las señales más claras
# de automatización. Estos dos van siempre; de la bolsa se sacan 1 o 2 al azar.
HASHTAG_FIJOS = ["#NFL", "#NowFootball"]
HASHTAG_BOLSA = [
    "#Football", "#NFLStats", "#FantasyFootball", "#Gridiron",
    "#NFLTwitter", "#ProFootball", "#NFLNews", "#GameDay",
]
HASHTAG_EXTRA = (1, 2)      # cuántos sacar de la bolsa, mínimo y máximo

# El crédito también rota, por la misma razón.
CREDITO_VARIANTES = [
    "📊 vía @{author}",
    "vía @{author}",
    "📊 @{author}",
    "Fuente: @{author}",
    "— @{author}",
]

# ---------- Archivos de estado ----------
QUEUE_FILE  = "state/queue.json"
POSTED_FILE = "state/posted.json"

TZ = ZoneInfo("America/Mazatlan")
