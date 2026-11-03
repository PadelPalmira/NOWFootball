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
# True  = deja los posts PROGRAMADOS en Facebook 24 h antes, para que los
#         revises en Meta Business Suite y canceles el que no te convenza.
# False = publica de inmediato.
MODO_REVISION       = True
HORAS_ANTICIPACION  = 24

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
MATURITY_HOURS     = 8      # un tweet debe tener al menos estas horas para ser elegible
                            # (si no, aún no acumuló reposts y lo juzgaríamos mal)
MAX_QUEUE_AGE_DAYS = 10     # después de esto se descarta de la cola
MIN_RETWEETS       = 15     # piso absoluto de calidad
QUEUE_HARD_LIMIT   = 400    # tope de la cola para que el JSON no crezca sin control

# Penalización por antigüedad al elegir (prefiere lo fresco, pero deja usable el backlog)
DECAY = [
    (48,  1.00),   # menos de 48h -> sin penalización
    (120, 0.85),   # menos de 5 días
    (999, 0.70),   # más viejo
]

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
