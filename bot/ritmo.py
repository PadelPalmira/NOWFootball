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

def tope_de_hoy(posted, ahora):
    """Aplica el arranque gradual. Devuelve (tope, nota)."""
    momentos = momentos_programados(posted)
    if not momentos:
        primer_tope = config.RAMPA[0][1] if config.RAMPA else config.TOPE_DIARIO
        return primer_tope, "primer día"
    dias = (ahora - min(momentos)).days
    for limite_dias, tope in config.RAMPA:
        if dias < limite_dias:
            return tope, f"arranque gradual, día {dias}"
    return config.TOPE_DIARIO, "ritmo normal"


def cuenta_del_dia(posted, fecha_local):
    return sum(1 for m in momentos_programados(posted)
               if _local(m).date() == fecha_local)


def cuenta_de_la_semana(posted, ahora):
    corte = ahora - dt.timedelta(days=7)
    return sum(1 for m in momentos_programados(posted) if m > corte)


def slots_restantes(hora_local_actual):
    """Cuántos turnos quedan hoy, contando el actual."""
    quedan = [h for h in config.SLOTS_LOCALES if h >= hora_local_actual]
    return max(len(quedan), 1)


# ---------------------------------------------------------------- la decisión

def momento_objetivo(ahora, rng):
    """A qué hora saldría la publicación, con el desorden aplicado."""
    base = ahora
    if config.MODO_REVISION:
        base = ahora + dt.timedelta(hours=config.HORAS_ANTICIPACION)
    desfase = rng.randint(-config.JITTER_MINUTOS, config.JITTER_MINUTOS)
    objetivo = base + dt.timedelta(minutes=desfase)

    # Nunca fuera de la ventana horaria local
    local = _local(objetivo)
    if local.hour < config.VENTANA_INICIO:
        local = local.replace(hour=config.VENTANA_INICIO,
                              minute=rng.randint(5, 50), second=0, microsecond=0)
    elif local.hour >= config.VENTANA_FIN:
        local = local.replace(hour=config.VENTANA_FIN - 1,
                              minute=rng.randint(5, 50), second=0, microsecond=0)
    objetivo = local.astimezone(dt.timezone.utc)

    # Facebook exige al menos 10 minutos de anticipación para programar
    if config.MODO_REVISION:
        minimo = ahora + dt.timedelta(minutes=20)
        if objetivo < minimo:
            objetivo = minimo
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
    fecha = _local(objetivo).date()

    tope, nota = tope_de_hoy(posted, ahora)
    hoy = cuenta_del_dia(posted, fecha)
    if hoy >= tope:
        return False, (f"Cupo del día lleno: ya hay {hoy} de {tope} "
                       f"para el {fecha} ({nota})."), None

    semana = cuenta_de_la_semana(posted, ahora)
    if semana >= config.TOPE_SEMANAL:
        return False, f"Tope semanal alcanzado ({semana} de {config.TOPE_SEMANAL}).", None

    momentos = momentos_programados(posted)
    if momentos:
        hueco = abs((objetivo - momentos[-1]).total_seconds()) / 3600.0
        if hueco < config.MIN_HORAS_ENTRE_POSTS:
            return False, (f"Queda muy pegado al anterior "
                           f"({hueco:.1f} h; el mínimo es "
                           f"{config.MIN_HORAS_ENTRE_POSTS} h)."), None

    # Repartir el cupo que queda entre los turnos que quedan del día, para que
    # no se gasten todos en la mañana y las tardes queden siempre vacías.
    quedan = slots_restantes(_local(ahora).hour)
    cupo = tope - hoy
    probabilidad = min(1.0, cupo / quedan)
    if rng.random() > probabilidad:
        return False, (f"Turno saltado a propósito (quedan {cupo} de cupo para "
                       f"{quedan} turnos; probabilidad {probabilidad:.0%}). "
                       f"Esto es lo que evita el patrón de reloj."), None

    return True, f"{hoy + 1} de {tope} del día ({nota})", objetivo
