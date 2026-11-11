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
RETRASO_MINUTOS = (20, 40)

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

# --- Reparto del cupo a lo largo del día (v1.15) -------------------------
# El reloj de GitHub se come turnos cuando está cargado. Antes el cupo se
# repartía entre los turnos que faltaban y, al no llegar, el día cerraba
# muy por debajo del cupo. Ahora, si vamos atrasados respecto a lo que
# tocaría a esta hora, se publica sin sortear.
# Si vamos al corriente o atrasados se publica. Si vamos adelantados, esta
# es la probabilidad de publicar igual (baja: para eso es el freno).
PROBABILIDAD_ADELANTO = 0.35

# --- Historial acotado (v1.15) ------------------------------------------
# El registro de publicados se guarda en el repositorio en cada corrida, así
# que no puede crecer para siempre. Lo único que NUNCA se tira es el id y la
# huella (phash): son los que impiden republicar una imagen.
DIAS_MARCAS     = 7     # marcas de "repetida": se borran pasados estos días
DIAS_DETALLE    = 120   # publicados: pasados estos días se dejan solo lo esencial
TOPE_HISTORIAL  = 4000  # tope duro de entradas en el historial


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
TWEETS_PER_ACCOUNT = 14     # cuántos tweets recientes se revisan por cuenta
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

# ---------- Tarjeta ----------
# Hay UN SOLO diseño: fondo blanco, titular arriba, imagen completa al
# centro y el logo en una franja oscura abajo.
#
# Se eliminaron los dos diseños anteriores:
#   - La pantalla partida recortaba tanto la imagen que el post ya no se
#     parecía al original (un meme de "TRASH vs GARBAGE" acababa mostrando
#     "H GAR" y medio bote de basura).
#   - El vertical oscuro se quitó para que la página se vea pareja: un solo
#     formato es más reconocible que dos conviviendo.
# Por eso ya no existen CUENTAS_TARJETA ni el detector de gráficas: todas
# las cuentas reciben el mismo trato y ninguna imagen se recorta nunca.

TARJETA_MARGEN      = 54
TARJETA_TITULAR_MIN = 40
TARJETA_INTERLINEA  = 0.98        # Anton se ve mejor con los renglones pegados

BLANCO_TITULAR_MAX   = 78         # el titular se achica solo hasta que quepa
BLANCO_MAX_RENGLONES = 3

# El logo: antes decía 54 pero se VEÍA en 32. El archivo del logo trae mucho
# aire transparente alrededor, y al escalarlo tal cual ese aire se contaba
# como parte del alto. Ahora el dibujo se recorta primero, así que el número
# de aquí es el alto que de verdad se ve.
BLANCO_LOGO_ALTO = 118
BLANCO_FRANJA    = 190            # alto de la franja oscura que lo contiene

COLOR_TEXTO   = "#FFFFFF"
COLOR_TINTA   = "#0F1018"         # el titular sobre blanco
COLOR_RESALTE = "#FF1F6E"         # las palabras resaltadas, rosa de la marca
COLOR_FRANJA  = "#12141F"         # la franja del logo
BLANCO_FILO   = "#E4E8F0"         # filo tenue alrededor de la imagen


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
