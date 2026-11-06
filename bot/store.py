"""Lectura y escritura del estado en disco (cola de candidatos y registro de publicados).

Dos cosas importantes que se arreglaron en la v1.15:

ESCRITURA ATÓMICA. Antes se escribía directo sobre el archivo. Si GitHub
mataba la corrida a la mitad (se acabó el tiempo, se canceló), el archivo
quedaba cortado y el JSON ya no se podía leer. Y como al no poder leerlo se
devolvía un historial vacío, el bot creía que nunca había publicado nada:
habría vuelto a publicar lo mismo y habría reiniciado el cupo del día. Ahora
se escribe en un archivo temporal y se cambia de nombre al final, que es una
operación que el sistema no puede dejar a medias.

HISTORIAL ACOTADO. El registro de publicados crecía para siempre y se guarda
en el repositorio en cada corrida. Ahora se compacta: las marcas de
"repetida" viejas se borran y a los publicados viejos se les quitan los
campos de adorno. Lo que NUNCA se borra es el id y la huella (phash), que
son justo lo que impide republicar una imagen.
"""
import datetime as dt
import json
import os
import tempfile

from . import config

# Campos que se conservan siempre al compactar. El resto es informativo.
ESENCIALES = ("id", "phash", "image_url", "at", "publica_en", "author", "skipped")


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError, ValueError):
        return default


def _save(path, data):
    """Guarda sin dejar el archivo a medias si la corrida se interrumpe."""
    carpeta = os.path.dirname(path) or "."
    os.makedirs(carpeta, exist_ok=True)
    fd, temporal = tempfile.mkstemp(dir=carpeta, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temporal, path)       # atómico: o está el viejo o el nuevo
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def load_queue():
    q = _load(config.QUEUE_FILE, {})
    if not isinstance(q, dict):
        return {}
    # Solo entradas con forma de diccionario; una entrada rara tiraba la corrida
    return {k: v for k, v in q.items() if isinstance(v, dict)}


def save_queue(q):
    _save(config.QUEUE_FILE, q)


def load_posted():
    data = _load(config.POSTED_FILE, {"items": []})
    if isinstance(data, list):              # compatibilidad con formato viejo
        data = {"items": data}
    if not isinstance(data, dict):          # null, texto, número...
        data = {"items": []}
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    data["items"] = [i for i in items if isinstance(i, dict)]
    return data


def save_posted(p):
    _save(config.POSTED_FILE, compactar(p))


def _fecha(item):
    crudo = item.get("at") or item.get("publica_en")
    if not isinstance(crudo, str):
        return None
    try:
        d = dt.datetime.fromisoformat(crudo)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def compactar(posted, ahora=None):
    """Acota el historial sin perder la capacidad de detectar repetidas.

    - Las marcas de "repetida" de más de DIAS_MARCAS días se borran: el tweet
      ya salió de la cola, así que la marca no sirve para nada.
    - A los publicados de más de DIAS_DETALLE días se les quitan los campos
      informativos y se queda lo esencial (id, huella, fecha).
    - Si aun así hay más de TOPE_HISTORIAL, se tiran los más viejos.
    """
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    items = posted.get("items", [])

    corte_marcas = ahora - dt.timedelta(days=config.DIAS_MARCAS)
    corte_detalle = ahora - dt.timedelta(days=config.DIAS_DETALLE)

    limpios = []
    for item in items:
        fecha = _fecha(item)
        if item.get("skipped") and fecha and fecha < corte_marcas:
            continue                                  # marca vieja, se va
        if fecha and fecha < corte_detalle and len(item) > len(ESENCIALES):
            item = {k: v for k, v in item.items() if k in ESENCIALES}
        limpios.append(item)

    if len(limpios) > config.TOPE_HISTORIAL:
        con_fecha = [(_fecha(i) or dt.datetime.min.replace(tzinfo=dt.timezone.utc), n, i)
                     for n, i in enumerate(limpios)]
        con_fecha.sort(key=lambda t: (t[0], t[1]))
        limpios = [i for _, _, i in con_fecha[-config.TOPE_HISTORIAL:]]

    salida = dict(posted)
    salida["items"] = limpios
    return salida


def posted_ids(posted):
    return {str(i.get("id")) for i in posted.get("items", []) if i.get("id")}
