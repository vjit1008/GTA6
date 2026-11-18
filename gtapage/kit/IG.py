"""Instagram publishing (Instagram API with Instagram Login). Needs secrets: IG_USER_ID (digits), IG_ACCESS_TOKEN (IGAA...),
CLOUDINARY_CLOUD_NAME + CLOUDINARY_UPLOAD_PRESET (unsigned preset; Instagram needs a public URL for each file)."""
import os
import time

import requests

API = "https://graph.instagram.com/v21.0"


class TokenError(Exception):
    pass


def _env(n):
    v = os.getenv(n)
    if not v:
        raise TokenError(f"secret {n} is missing")
    return v


def upload(path, video=False):
    cloud, preset = _env("CLOUDINARY_CLOUD_NAME"), _env("CLOUDINARY_UPLOAD_PRESET")
    kind = "video" if video else "image"
    with open(path, "rb") as f:
        r = requests.post(f"https://api.cloudinary.com/v1_1/{cloud}/{kind}/upload", data={"upload_preset": preset}, files={"file": f}, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Cloudinary upload failed: {r.status_code} {r.text[:200]}")
    return r.json()["secure_url"]


def _post(path, **data):
    data["access_token"] = _env("IG_ACCESS_TOKEN")
    r = requests.post(f"{API}/{path}", data=data, timeout=120)
    j = r.json() if r.content else {}
    if not r.ok:
        err = j.get("error", {})
        if err.get("code") in (190, 102, 10, 200) or r.status_code in (401, 403):
            raise TokenError(f"Instagram refused: {err.get('message', r.text[:200])}")
        raise RuntimeError(f"Instagram error {r.status_code}: {err.get('message', r.text[:200])}")
    return j


def _wait(cid, tries=40):
    tok = _env("IG_ACCESS_TOKEN")
    for _ in range(tries):
        r = requests.get(f"{API}/{cid}", params={"fields": "status_code,status", "access_token": tok}, timeout=60).json()
        s = r.get("status_code")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {r}")
        time.sleep(6)
    raise RuntimeError("Instagram processing timed out")


def _publish(cid):
    _wait(cid)
    return _post(f"{_env('IG_USER_ID')}/media_publish", creation_id=cid)["id"]


def image(path, caption):
    c = _post(f"{_env('IG_USER_ID')}/media", image_url=upload(path), caption=caption)["id"]
    return _publish(c)


def carousel(paths, caption):
    uid = _env("IG_USER_ID")
    kids = []
    for p in paths:
        k = _post(f"{uid}/media", image_url=upload(p), is_carousel_item="true")["id"]
        _wait(k)
        kids.append(k)
    c = _post(f"{uid}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    return _publish(c)


def reel(path, caption):
    c = _post(f"{_env('IG_USER_ID')}/media", media_type="REELS", video_url=upload(path, True), caption=caption, share_to_feed="true")["id"]
    return _publish(c)


def diagnose():
    r = requests.get(f"{API}/me", params={"fields": "user_id,username,account_type", "access_token": _env("IG_ACCESS_TOKEN")}, timeout=60)
    print(r.status_code, r.text[:300])
    lim = requests.get(f"{API}/{_env('IG_USER_ID')}/content_publishing_limit", params={"fields": "quota_usage,config", "access_token": _env("IG_ACCESS_TOKEN")}, timeout=60)
    print("publishing quota:", lim.status_code, lim.text[:300])
