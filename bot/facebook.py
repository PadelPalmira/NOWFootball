"""Publica una foto en la página de Facebook vía Graph API."""
import requests

from . import config


def post_photo(image_path, message, page_id=None, token=None, api_version=None):
    page_id = page_id or config.FB_PAGE_ID
    token = token or config.FB_PAGE_TOKEN
    api_version = api_version or config.FB_API_VERSION
    if not page_id or not token:
        raise RuntimeError("Faltan FB_PAGE_ID o FB_PAGE_TOKEN")

    url = f"https://graph.facebook.com/{api_version}/{page_id}/photos"
    with open(image_path, "rb") as fh:
        r = requests.post(
            url,
            data={"message": message, "access_token": token},
            files={"source": fh},
            timeout=120,
        )
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text}
    if r.status_code >= 400:
        raise RuntimeError(f"Facebook rechazó la publicación ({r.status_code}): {body}")
    return body
