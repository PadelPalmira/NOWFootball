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
HASHTAGS = "#NFL #NowFootball #Football #NFLStats #FantasyFootball #Gridiron"
CREDIT_TEMPLATE = "📊 vía @{author}"

# ---------- Archivos de estado ----------
QUEUE_FILE  = "state/queue.json"
POSTED_FILE = "state/posted.json"

TZ = ZoneInfo("America/Mazatlan")
