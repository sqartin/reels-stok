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
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://graph.facebook.com/v21.0"
UPLOAD = "https://rupload.facebook.com/ig-api-upload/v21.0"
ARALIK = int(os.environ.get("ARALIK_DK", "710"))
TOKEN = os.environ["IG_TOKEN"]
IG_ID = os.environ["IG_ID"]
SERI_SAAT = int(os.environ.get("SERI_SAAT", "19"))
SERI_BASLANGIC = os.environ.get("SERI_BASLANGIC", "2026-11-23")  # bu tarihten once seri paylasilmaz


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


def yukle_yayinla(surum, ad, aciklama):
    """Instagram videoyu deponun herkese acik surum dosyasindan kendisi ceker (video_url)."""
    url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/download/{surum}/{ad}"
    kap = istek(f"{API}/{IG_ID}/media", {"media_type": "REELS", "video_url": url, "caption": aciklama,
                                         "share_to_feed": "true", "access_token": TOKEN})["id"]
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


def varliklar_oku(surum):
    try:
        return json.loads(gh("release", "view", surum, "--json", "assets"))["assets"]
    except subprocess.CalledProcessError:
        return []


def paylas(surum, varliklar, ad):
    txt = ad[:-4] + ".txt"
    aciklama = ""
    if any(x["name"] == txt for x in varliklar):
        Path("indir").mkdir(exist_ok=True)
        gh("release", "download", surum, "--pattern", txt, "--dir", "indir", "--clobber")
        aciklama = (Path("indir") / txt).read_text(encoding="utf-8").strip()
    print(f"Paylasiliyor: {ad}")
    for deneme in range(4):
        try:
            sonuc = yukle_yayinla(surum, ad, aciklama)
            break
        except RuntimeError as e:
            print(f"Deneme {deneme + 1} basarisiz: {e}")
            if deneme == 3:
                raise
            time.sleep(30)
    print(f"YAYINLANDI medya id: {sonuc['id']}")
    for a in (ad, txt):
        if any(x["name"] == a for x in varliklar):
            gh("release", "delete-asset", surum, a, "--yes")


def main():
    # 1) Seri modu: "seri" surumunde bolum varsa her gun SERI_SAAT'te (Turkiye saati) siradaki bolum paylasilir,
    #    seri bitene kadar baska video paylasilmaz.
    seri = sorted(a["name"] for a in varliklar_oku("seri") if a["name"].endswith(".mp4"))
    if seri:
        simdi = datetime.now(timezone.utc) + timedelta(hours=3)
        hedef = simdi.replace(hour=SERI_SAAT, minute=0, second=0, microsecond=0)
        if simdi.strftime("%Y-%m-%d") < SERI_BASLANGIC or simdi < hedef:
            print(f"Seri: siradaki {seri[0]}, saat {SERI_SAAT}.00 bekleniyor.")
            return
        if son_paylasim_dk() < (simdi - hedef).total_seconds() / 60:
            print("Seri: bugunun bolumu paylasilmis.")
            return
        paylas("seri", varliklar_oku("seri"), seri[0])
        return
    # 2) Normal mod: stoktan ARALIK dakikada bir
    gecen = son_paylasim_dk()
    if gecen < ARALIK:
        print(f"Son paylasim {gecen:.0f} dk once, bekleniyor.")
        return
    varliklar = varliklar_oku("stok")
    videolar = sorted([a for a in varliklar if a["name"].endswith(".mp4")],
                      key=lambda a: (not a["name"].startswith("kesit_"), a["createdAt"]))
    if not videolar:
        print("Stok bos.")
        return
    paylas("stok", varliklar, videolar[0]["name"])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"HATA: {e}")
        sys.exit(1)
