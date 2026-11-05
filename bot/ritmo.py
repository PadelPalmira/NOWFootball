"""Decide si toca publicar en esta corrida, y a qué hora exacta.

Toda la lógica de "no parecer un robot" vive aquí:
  - cupo diario, repartido parejo entre los turnos que quedan del día
  - arranque gradual durante las primeras dos semanas
  - desorden aleatorio en la hora, para no caer siempre en punto
  - separación mínima entre publicaciones
  - ventana horaria
  - botón de pausa y freno por fallos seguidos
"""
import datetime as dt
import os
import random

from . import config


def es_manual():
    """True cuando le picaste al botón tú, en vez de dispararse el reloj.

    El salto aleatorio de turnos existe para que el bot no parezca un reloj.
    En una prueba manual solo estorba: contestaría "turno saltado" y parecería
    que algo está roto. Los demás frenos (pausa, cupo, horario, separación
    mínima) sí se respetan siempre.
    """
    return os.environ.get("CORRIDA_MANUAL", "").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------- utilidades

def _local(momento):
    return momento.astimezone(config.TZ)


def _iso(momento):
    return momento.astimezone(dt.timezone.utc).isoformat()


def momentos_programados(posted):
    """Fechas-hora (UTC) de todo lo que ya se publicó o quedó programado."""
    fuera = []
    for item in posted.get("items", []):
        if item.get("skipped"):
            continue
        crudo = item.get("publica_en") or item.get("at")
        if not crudo:
            continue
        try:
            d = dt.datetime.fromisoformat(crudo)
        except ValueError:
            continue
        fuera.append(d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc))
    return sorted(fuera)


def en_pausa():
    return os.path.exists(config.ARCHIVO_PAUSA)


def fallos_seguidos(posted):
    return int(posted.get("fallos_seguidos", 0) or 0)


# ------------------------------------------------------------------- límites

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def tope_del_dia_semana(fecha_local):
    """Cuántas publicaciones permite ese día. Domingo, lunes y jueves son
    días de partido y llevan más."""
    dia = fecha_local.weekday()
    return config.TOPE_POR_DIA.get(dia, config.TOPE_DIARIO), DIAS[dia]


def tope_de_hoy(posted, ahora, fecha_local=None):
    """Devuelve (tope, nota). Durante las dos primeras semanas manda el
    arranque gradual; después, el cupo del día de la semana."""
    fecha_local = fecha_local or _local(ahora).date()
    tope_dia, nombre = tope_del_dia_semana(fecha_local)

    momentos = momentos_programados(posted)
    if not momentos:
        primer = config.RAMPA[0][1] if config.RAMPA else tope_dia
        return min(primer, tope_dia), "primer día"
    dias = (ahora - min(momentos)).days
    for limite_dias, tope in config.RAMPA:
        if dias < limite_dias:
            return min(tope, tope_dia), f"arranque gradual, día {dias}"
    return tope_dia, nombre


def cuenta_del_dia(posted, fecha_local):
    return sum(1 for m in momentos_programados(posted)
               if _local(m).date() == fecha_local)


def cuenta_de_la_semana(posted, ahora):
    corte = ahora - dt.timedelta(days=7)
    return sum(1 for m in momentos_programados(posted) if m > corte)


def slots_restantes(hora_local_actual):
    """Cuántos turnos quedan hoy, contando el actual.

    Los turnos van cada hora y media, así que hay medias horas. Se da un
    margen de 10 minutos para que un arranque tardío del reloj de GitHub
    siga contando como el turno que le toca.
    """
    quedan = [h for h in config.SLOTS_LOCALES if h >= hora_local_actual - 0.17]
    return max(len(quedan), 1)


# ---------------------------------------------------------------- la decisión

def momento_objetivo(ahora, rng):
    """Cuándo sale la publicación. None = al instante.

    El retraso es corto y aleatorio: desordena la hora (publicar al instante
    la dejaría clavada en la hora del cron) y da margen para cancelar.
    """
    minimo, maximo = config.RETRASO_MINUTOS
    if maximo <= 0:
        return None

    minutos = rng.randint(max(minimo, 11), max(maximo, 11))
    objetivo = ahora + dt.timedelta(minutes=minutos)

    # Que el retraso no empuje la publicación fuera de la ventana horaria
    local = _local(objetivo)
    if local.hour >= config.VENTANA_FIN or local.hour < config.VENTANA_INICIO:
        return None
    return objetivo


def decidir(posted, ahora=None, rng=None):
    """Devuelve (publicar: bool, razon: str, momento: datetime|None)."""
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    rng = rng or random

    if en_pausa():
        return False, (f"El bot está en PAUSA: existe el archivo "
                       f"'{config.ARCHIVO_PAUSA}' en el repositorio. "
                       f"Bórralo desde GitHub para reanudar."), None

    fallos = fallos_seguidos(posted)
    if fallos >= config.MAX_FALLOS_SEGUIDOS:
        return False, (f"Detenido por seguridad: Facebook rechazó las últimas "
                       f"{fallos} publicaciones seguidas. Corre el botón 1 para "
                       f"ver qué pasa. Al publicar bien una vez, el contador se "
                       f"reinicia solo."), None

    objetivo = momento_objetivo(ahora, rng)
    local_ahora = _local(ahora)
    if not (config.VENTANA_INICIO <= local_ahora.hour < config.VENTANA_FIN):
        return False, (f"Fuera de la ventana de publicación "
                       f"({config.VENTANA_INICIO}:00 a {config.VENTANA_FIN}:00, "
                       f"hora de Mazatlán)."), None
    if config.RETRASO_MINUTOS[1] > 0 and objetivo is None:
        return False, "El retraso dejaría la publicación fuera de la ventana horaria.", None
    fecha = _local(objetivo or ahora).date()

    tope, nota = tope_de_hoy(posted, ahora, fecha)
    hoy = cuenta_del_dia(posted, fecha)
    if hoy >= tope:
        return False, (f"Cupo del día lleno: ya hay {hoy} de {tope} "
                       f"para el {fecha} ({nota})."), None

    semana = cuenta_de_la_semana(posted, ahora)
    if semana >= config.TOPE_SEMANAL:
        return False, f"Tope semanal alcanzado ({semana} de {config.TOPE_SEMANAL}).", None

    momentos = momentos_programados(posted)
    if momentos:
        hueco = abs(((objetivo or ahora) - momentos[-1]).total_seconds()) / 3600.0
        if hueco < config.MIN_HORAS_ENTRE_POSTS:
            return False, (f"Queda muy pegado al anterior "
                           f"({hueco:.1f} h; el mínimo es "
                           f"{config.MIN_HORAS_ENTRE_POSTS} h)."), None

    # Repartir el cupo que queda entre los turnos que quedan del día, para que
    # no se gasten todos en la mañana y las tardes queden siempre vacías.
    local = _local(ahora)
    quedan = slots_restantes(local.hour + local.minute / 60.0)
    cupo = tope - hoy
    probabilidad = min(1.0, cupo / quedan)
    if es_manual():
        return True, (f"{hoy + 1} de {tope} del día ({nota}) · corrida manual, "
                      f"no se aplica el salto aleatorio"), objetivo
    if rng.random() > probabilidad:
        return False, (f"Turno saltado a propósito (quedan {cupo} de cupo para "
                       f"{quedan} turnos; probabilidad {probabilidad:.0%}). "
                       f"Esto es lo que evita el patrón de reloj."), None

    return True, f"{hoy + 1} de {tope} del día ({nota})", objetivo
