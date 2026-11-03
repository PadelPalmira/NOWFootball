"""Lectura y escritura del estado en disco (cola de candidatos y registro de publicados)."""
import json
import os

from . import config


def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)


def load_queue():
    return _load(config.QUEUE_FILE, {})


def save_queue(q):
    _save(config.QUEUE_FILE, q)


def load_posted():
    data = _load(config.POSTED_FILE, {"items": []})
    if isinstance(data, list):          # compatibilidad con formato viejo
        data = {"items": data}
    data.setdefault("items", [])
    return data


def save_posted(p):
    _save(config.POSTED_FILE, p)


def posted_ids(posted):
    return {str(i.get("id")) for i in posted.get("items", []) if i.get("id")}


