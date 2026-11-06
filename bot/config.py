"""Configuración central del bot de Now Football."""
import os
from zoneinfo import ZoneInfo

# ---------- Cuentas de X a monitorear ----------
ACCOUNTS = [
    "NFL_Stats",
    "SleeperNFL",
    "NFL_DovKleiman",
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
# Horas locales a las que el bot despierta, cada hora y media. El código
# decide en cuáles publica de verdad, repartiendo el cupo del día.
# Son 10 turnos porque en día de partido el cupo sube a 9: con 8 turnos
# ese cupo sería inalcanzable.
SLOTS_LOCALES   = [8.0, 9.5, 11.0, 12.5, 14.0, 15.5, 17.0, 18.5, 20.0, 21.5]
VENTANA_INICIO  = 8         # no se programa nada antes de esta hora local
VENTANA_FIN     = 23        # ni después de esta
JITTER_MINUTOS  = 25        # desorden aleatorio, para no caer siempre en punto

# La NFL tiene un ritmo semanal fuerte: el domingo hay partidos todo el día,
# el lunes y el jueves hay partido de noche, y el martes y el miércoles casi
# no pasa nada. Por eso el cupo cambia según el día.
# Numeración de Python: lunes=0, martes=1, ... domingo=6
TOPE_POR_DIA = {6: 9, 0: 9, 3: 9}   # domingo, lunes y jueves
TOPE_DIARIO  = 6                     # el resto de los días
TOPE_SEMANAL = 55

# Con 9 publicaciones en una ventana de 15 horas, el hueco promedio es de
# 100 minutos. El mínimo baja a 1 hora para que ese cupo sea alcanzable.
MIN_HORAS_ENTRE_POSTS = 1.0

# Arranque gradual: (días desde la primera publicación, tope de ese periodo).
# Pasados los 14 días se usa TOPE_DIARIO. Un salto repentino de ritmo llama
# más la atención que el ritmo en sí.
RAMPA = [(7, 3), (14, 4)]

NO_REPETIR_CUENTA_SEGUIDA = True

# ---------- Filtro de contenido ----------
# Si alguna de estas aparece en el texto del tweet, no se publica. Sirve
# sobre todo para los anuncios pagados: las cuentas agregadoras meten
# promociones de casas de apuestas entre sus notas, y publicar el anuncio de
# otro en tu página no tiene sentido.
PALABRAS_VETADAS = [
    "sponsored", "#ad", "ad:", "promo code", "sign up", "use code",
    "odds boost", "bet now", "risk-free", "deposit bonus", "giveaway",
    "888sport", "bet365", "draftkings", "fanduel", "betmgm", "caesars",
    "gambling problem", "21+", "terms apply",
]

# ---------- Frenos de emergencia ----------
# Si existe un archivo con este nombre en el repositorio, el bot no publica
# nada. Crearlo o borrarlo desde GitHub es un clic.
ARCHIVO_PAUSA       = "PAUSA"
BLOQUEADOS_FILE     = "state/bloqueados.json"
MAX_FALLOS_SEGUIDOS = 3     # tras estos fallos de Facebook, el bot se detiene

# ---------- Reglas de selección ----------
TWEETS_PER_ACCOUNT = 20     # cuántos tweets recientes se revisan por cuenta
MAX_QUEUE_AGE_DAYS = 3      # después de esto se descarta de la cola
# Medir solo reposts no servía con estas cuentas: la mediana es de 7 reposts
# y la mitad de los candidatos empatan en 2 o 3, así que el desempate salía
# casi al azar. Los likes dan 11 veces más señal, así que se mide el
# engagement combinado, con el repost pesando más porque cuesta más darlo.
PESO_REPOST        = 3      # cuánto vale un repost frente a un like
MIN_ENGAGEMENT     = 25     # piso de tracción (reposts*PESO + likes)
MIN_RETWEETS       = 0      # ya no se usa como filtro; queda por compatibilidad
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

# ---------- Lienzo ----------
CANVAS_W, CANVAS_H = 1080, 1350
LOGO_PATH    = "assets/logo.png"
PHASH_DISTANCE = 6

# ---------- Tarjeta (pantalla partida) ----------
# Diseño: foto a la derecha con halo de neón, titular y lista a la izquierda.
USAR_TARJETA = True

# El formato de tarjeta es el estándar para TODO lo que publican las cuentas
# aprobadas, sin importar el tema. Si alguna vez sale una imagen que ya es
# una gráfica de estadísticas y se ve partida a la mitad, poner esto en False
# reactiva el detector que la deja completa.
TARJETA_SIEMPRE = True


# Solo estas cuentas reciben el diseño de pantalla partida. Si más adelante
# agregas una cuenta a ACCOUNTS, NO entra aquí sola: hay que revisarla
# primero. Algunas cuentas (BetMGM, por ejemplo) marcan sus fotos con el
# logo del patrocinador, y eso necesita un paso extra antes de usarlas.
# @NFL_DovKleiman NO está aquí todavía, a propósito: publica muchas capturas
# de pantalla de otros tweets, y partir una captura a la mitad la deja
# ilegible. No pude calibrar un detector de capturas sin imágenes reales
# suyas. Mientras tanto sus posts usan el diseño anterior, que funciona con
# capturas y con fotos. En cuanto haya tweets suyos en la cola se revisa y
# se agrega aquí.
CUENTAS_TARJETA = ["NFL_Stats", "SleeperNFL"]

TARJETA_PROPORCION_TEXTO = 0.52   # cuánto del ancho ocupa el panel de texto
TARJETA_MARGEN       = 54
TARJETA_TITULAR_MAX  = 86         # el titular se achica solo hasta que quepa
TARJETA_TITULAR_MAX_SOLO = 112    # cuando el tweet no trae lista, cabe más grande

# Diseño vertical: imagen completa al centro, titular arriba, logo abajo.
# Es el que se usa cuando partir la imagen la arruinaría (gráficas que ya
# traen sus datos, capturas de pantalla de otros tweets).
VERTICAL_TITULAR_MAX   = 82
VERTICAL_MAX_RENGLONES = 4
VERTICAL_HUECO         = 30
VERTICAL_SESGO_IMAGEN  = 0.68     # 0 = pegada al texto, 1 = pegada al logo
TARJETA_TITULAR_MIN  = 40
TARJETA_LISTA_MIN    = 32
TARJETA_LISTA_RATIO  = 0.50       # tamaño de la lista respecto al titular
TARJETA_LOGO_ALTO    = 54
TARJETA_AURA         = True
TARJETA_AURA_RADIO   = 14
TARJETA_AURA_FUERZA  = 0.55
TARJETA_GLOW_RADIO   = 13
TARJETA_GLOW_FUERZA  = 1.25        # qué tan encendido queda el neón
TARJETA_INTERLINEA   = 0.98       # Anton se ve mejor con los renglones pegados
TARJETA_HUECO_LISTA  = 46         # aire entre el titular y la lista
TARJETA_SESGO_VERTICAL = 0.42     # 0 = pegado arriba, 1 = pegado abajo

COLOR_FONDO_1 = "#0A1020"         # arriba del degradado
COLOR_FONDO_2 = "#141C33"         # abajo
COLOR_TEXTO   = "#FFFFFF"
COLOR_RESALTE        = "#FF1F6E"  # el halo del neón
COLOR_RESALTE_NUCLEO = "#FF8FBE"  # el núcleo, más claro, para que se lea
COLOR_LISTA   = "#D8DEEC"
COLOR_AURA    = "#FF2D78"

# Detector de foto vs tarjeta de estadísticas. Se marca como gráfica cuando
# se cumplen al menos dos de los tres criterios.
GRAFICA_DOMINIO  = 0.62    # fracción de la imagen que ocupan 6 colores
GRAFICA_VARIEDAD = 0.22    # colores distintos entre píxeles
GRAFICA_PLANICIE = 0.55    # fracción de píxeles idénticos a su vecino


# ---------- Redactor con IA ----------
# Un modelo escribe el caption a partir del texto del tweet: le pone gancho
# y, a veces, una pregunta para provocar comentarios. Si la llamada falla o
# el resultado no pasa las validaciones, se usa el texto original tal cual:
# el bot nunca deja de publicar por esto.
USAR_IA            = True
IA_MODELO          = "claude-haiku-5-5"
IA_MAX_TOKENS      = 300
IA_TIMEOUT         = 25
IA_PROB_PREGUNTA   = 0.40   # en qué proporción de posts pide una pregunta final
IA_MAX_CARACTERES  = 320    # si se pasa, se descarta y se usa el original

# ---------- Caption ----------
# La marca de la página: va al principio de TODAS las publicaciones, con dos
# espacios, barra vertical y dos espacios antes del texto.
#     #NFL  |  Texto de la publicación
HASHTAG_MARCA   = "#NFL"
SEPARADOR_MARCA = "  |  "

# Un emoji al inicio del texto, elegido según de qué trata la publicación.
# Las malas noticias (lesiones, castigos, fallecimientos) llevan uno sobrio o
# ninguno: un 🔥 sobre una lesión se ve pésimo.
USAR_EMOJIS = True

# Mandar siempre el mismo bloque de hashtags es una de las señales más claras
# de automatización. Este va siempre abajo; de la bolsa se sacan 1 o 2 al azar.
HASHTAG_FIJOS = ["#NowFootball"]
HASHTAG_BOLSA = [
    "#Football", "#NFLStats", "#FantasyFootball", "#Gridiron",
    "#NFLTwitter", "#ProFootball", "#NFLNews", "#GameDay",
]
HASHTAG_EXTRA = (1, 2)      # cuántos sacar de la bolsa, mínimo y máximo

# El crédito también rota, por la misma razón.
CREDITO_VARIANTES = [
    "📊 via @{author}",
    "via @{author}",
    "📊 @{author}",
    "Source: @{author}",
    "— @{author}",
    "h/t @{author}",
]

# ---------- Archivos de estado ----------
QUEUE_FILE  = "state/queue.json"
POSTED_FILE = "state/posted.json"

TZ = ZoneInfo("America/Mazatlan")
