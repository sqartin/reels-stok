"""GitHub Actions'ta calisan bulut paylasimcisi.

Stok: bu deponun "stok" adli GitHub Release'indeki .mp4 + .txt dosyalari.
Her calismada: Instagram'daki son paylasim en az ARALIK dakika once ise,
stoktaki en eski videoyu Reel olarak paylasir ve stoktan siler.
Ortam degiskenleri: IG_TOKEN, IG_ID (secret), GH_TOKEN + GITHUB_REPOSITORY (Actions verir).
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://graph.facebook.com/v21.0"
UPLOAD = "https://rupload.facebook.com/ig-api-upload/v21.0"
ARALIK = int(os.environ.get("ARALIK_DK", "115"))
TOKEN = os.environ["IG_TOKEN"]
IG_ID = os.environ["IG_ID"]


def istek(url, veri=None, basliklar=None):
    if isinstance(veri, dict):
        veri = urllib.parse.urlencode(veri).encode()
    req = urllib.request.Request(url, data=veri, headers=basliklar or {})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API hatasi ({e.code}): {e.read().decode(errors='replace')[:300]}") from None


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def son_paylasim_dk():
    d = istek(f"{API}/{IG_ID}/media?fields=timestamp&limit=1&access_token={TOKEN}")
    if not d.get("data"):
        return 10**6
    ts = datetime.strptime(d["data"][0]["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
    return (datetime.now(timezone.utc) - ts).total_seconds() / 60


def yukle_yayinla(video, aciklama):
    kap = istek(f"{API}/{IG_ID}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": aciklama,
                                         "share_to_feed": "true", "access_token": TOKEN})["id"]
    veri = video.read_bytes()
    istek(f"{UPLOAD}/{kap}", veri, {"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(len(veri))})
    for _ in range(60):
        dur = istek(f"{API}/{kap}?fields=status_code,status&access_token={TOKEN}")
        if dur.get("status_code") == "FINISHED":
            break
        if dur.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram isleyemedi: {dur.get('status')}")
        time.sleep(10)
    else:
        raise RuntimeError("Isleme 10 dakikada bitmedi")
    return istek(f"{API}/{IG_ID}/media_publish", {"creation_id": kap, "access_token": TOKEN})


def main():
    gecen = son_paylasim_dk()
    if gecen < ARALIK:
        print(f"Son paylasim {gecen:.0f} dk once, bekleniyor.")
        return
    varliklar = json.loads(gh("release", "view", "stok", "--json", "assets"))["assets"]
    videolar = sorted([a for a in varliklar if a["name"].endswith(".mp4")], key=lambda a: (not a["name"].startswith("kesit_"), a["createdAt"]))
    if not videolar:
        print("Stok bos.")
        return
    v = videolar[0]
    ad = v["name"]
    txt = ad[:-4] + ".txt"
    Path("indir").mkdir(exist_ok=True)
    gh("release", "download", "stok", "--pattern", ad, "--pattern", txt, "--dir", "indir", "--clobber")
    video = Path("indir") / ad
    aciklama = (Path("indir") / txt).read_text(encoding="utf-8").strip() if (Path("indir") / txt).exists() else ""
    print(f"Paylasiliyor: {ad}")

    for deneme in range(4):
        try:
            sonuc = yukle_yayinla(video, aciklama)
            break
        except RuntimeError as e:
            print(f"Deneme {deneme + 1} basarisiz: {e}")
            if deneme == 3:
                # sirayi kilitlemesin: bozuk videoyu stoktan cikar (bilgisayarda kopyasi var)
                for a in (ad, txt):
                    if any(x["name"] == a for x in varliklar):
                        gh("release", "delete-asset", "stok", a, "--yes")
                raise
            time.sleep(30)
    print(f"YAYINLANDI medya id: {sonuc['id']}")
    for a in (ad, txt):
        if any(x["name"] == a for x in varliklar):
            gh("release", "delete-asset", "stok", a, "--yes")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"HATA: {e}")
        sys.exit(1)
