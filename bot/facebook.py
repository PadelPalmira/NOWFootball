"""Publica en la página de Facebook vía Graph API.

Dos modos:
  - inmediato  : sube la foto y la publica en el momento.
  - programado : deja el post agendado para más tarde, sin publicar. Aparece
                 en Meta Business Suite para que lo revises o lo canceles.
"""
import json

import requests

from . import config


def _url(camino, api_version=None):
    return f"https://graph.facebook.com/{api_version or config.FB_API_VERSION}/{camino}"


def _revisar(r):
    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = {"raw": r.text}
    if r.status_code >= 400 or "error" in cuerpo:
        err = cuerpo.get("error", cuerpo)
        mensaje = err.get("message", json.dumps(cuerpo)[:300]) if isinstance(err, dict) else str(err)
        codigo = err.get("code") if isinstance(err, dict) else None
        pista = ""
        if codigo == 190:
            pista = (" — El permiso de Facebook venció o se invalidó. Pasa si"
                     " cambiaste tu contraseña. Hay que sacar un token nuevo.")
        elif codigo in (4, 17, 32, 613):
            pista = (" — Facebook pide esperar: se hicieron demasiadas"
                     " peticiones. El bot se detiene y reintenta en el"
                     " siguiente turno.")
        elif codigo in (200, 10, 3):
            pista = (" — Falta un permiso. Revisa que el token traiga"
                     " pages_manage_posts.")
        raise RuntimeError(f"Facebook rechazó la petición ({r.status_code}): {mensaje}{pista}")
    return cuerpo


def post_photo(image_path, message, page_id=None, token=None,
               api_version=None, publicar_en=None):
    """Publica o programa una foto.

    publicar_en: None para publicar ya, o un datetime con zona horaria para
                 dejarlo programado.
    """
    page_id = page_id or config.FB_PAGE_ID
    token = token or config.FB_PAGE_TOKEN
    if not page_id or not token:
        raise RuntimeError("Faltan FB_PAGE_ID o FB_PAGE_TOKEN")

    if publicar_en is None:
        with open(image_path, "rb") as fh:
            r = requests.post(_url(f"{page_id}/photos", api_version),
                              data={"message": message, "access_token": token},
                              files={"source": fh}, timeout=120)
        datos = _revisar(r)
        return {"modo": "publicado",
                "post_id": datos.get("post_id") or datos.get("id"),
                "publica_en": None}

    # --- Programado: primero la foto sin publicar, luego el post agendado
    with open(image_path, "rb") as fh:
        r = requests.post(_url(f"{page_id}/photos", api_version),
                          data={"published": "false", "temporary": "true",
                                "access_token": token},
                          files={"source": fh}, timeout=120)
    foto = _revisar(r)
    foto_id = foto.get("id")
    if not foto_id:
        raise RuntimeError(f"Facebook no devolvió el id de la foto: {foto}")

    cuando = int(publicar_en.timestamp())
    r = requests.post(
        _url(f"{page_id}/feed", api_version),
        data={
            "message": message,
            "attached_media[0]": json.dumps({"media_fbid": foto_id}),
            "published": "false",
            "scheduled_publish_time": str(cuando),
            "access_token": token,
        },
        timeout=120,
    )
    datos = _revisar(r)
    return {"modo": "programado",
            "post_id": datos.get("id"),
            "publica_en": publicar_en.isoformat()}
