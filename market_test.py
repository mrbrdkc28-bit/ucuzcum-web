"""
UCUZCUM — MARKET API TESTI (Colab)

Bu sunucu (Anthropic) veri merkezi IP'si oldugundan cok site 403 veriyor.
Colab (Google IP) farkli davranabilir. Bu araci COLAB'da calistir.

Cerez gerekiyorsa: tarayicida F12 -> Network -> istegi bul -> sag tik
-> Copy -> Copy as cURL. Icindeki 'cookie:' satirini asagida
CEREZLER'e yapistir.

KULLANIM:
  ucuzcum-web'e yukle, sonra Colab'da:
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/market_test.py -o mt.py
  exec(open('mt.py').read())
"""

import json
import re
import urllib.error
import urllib.request

# Cerez gerekiyorsa buraya yapistir (ornek: "session=abc; token=xyz")
CEREZLER = ""

TARAYICI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, text/html, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="126", "Google Chrome";v="126"',
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

HEDEFLER = [
    ("Cagri API", "https://api.cagri.com/product/product/all/WEB?page=1&limit=5&sort=id,asc",
     "https://www.cagri.com/"),
    ("TK Koop", "https://www.tkkoop.com.tr/haftalik-kampanyalar/kat-kat-firsat",
     "https://www.tkkoop.com.tr/"),
    ("Ozdilek carousel",
     "https://api.ozdilekteyim.com/rest/v2/market-gecit-store/products/carousel"
     "?productIds=10001704,10003883,10001710&fields=CAROUSEL&lang=tr&curr=TRY",
     "https://www.ozdilekteyim.com/"),
    ("Hakmar API", "https://api.hakmarexpress.com.tr/api/home/initialize-v2",
     "https://www.hakmarexpress.com.tr/"),
    ("Ideal API", "https://www.ideal.com.tr/api/homepage",
     "https://www.ideal.com.tr/"),
    ("Onur360 API",
     "https://www.onur360.com/api/Product/GetProductCategoryHierarchy"
     "?c=trtry0000&productIds=2914,2917,2951",
     "https://www.onur360.com/"),
    ("Peynirci Baba", "https://www.peynircibaba.com/indirimli-urunler/",
     "https://www.peynircibaba.com/"),
]


def dene(ad, url, referer):
    print(f"\n{'='*60}\n{ad}\n  {url[:78]}")
    basliklar = dict(TARAYICI)
    basliklar["Referer"] = referer
    basliklar["Origin"] = referer.rstrip("/")
    if CEREZLER:
        basliklar["Cookie"] = CEREZLER
    istek = urllib.request.Request(url, headers=basliklar)
    try:
        with urllib.request.urlopen(istek, timeout=18) as c:
            ham = c.read()
            print(f"  durum: {c.status} | boyut: {len(ham)}")
            metin = ham.decode("utf-8", "ignore")
            try:
                veri = json.loads(metin)
                print("  >> JSON dondu")
                incele(veri)
            except Exception:
                fiyat = re.findall(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", metin)
                print(f"  >> HTML | fiyat kalibi: {len(fiyat)}"
                      + (f" ornek {fiyat[:3]}" if fiyat else ""))
    except urllib.error.HTTPError as h:
        print(f"  durum: {h.code} (hala engelli)")
    except Exception as e:
        print(f"  HATA: {type(e).__name__} {str(e)[:70]}")


def incele(veri, derinlik=0):
    """JSON icinde urun listesi + fiyat/indirim alani ara."""
    if derinlik > 4:
        return
    if isinstance(veri, dict):
        anahtarlar = list(veri.keys())
        print(f"    {'  '*derinlik}anahtarlar: {anahtarlar[:10]}")
        # fiyat izi
        fiyat_izi = [k for k in anahtarlar if any(
            x in k.lower() for x in ["price", "fiyat", "discount", "indirim",
                                     "old", "sale", "normal", "regular"])]
        if fiyat_izi:
            print(f"    {'  '*derinlik}>> FIYAT ALANLARI: {fiyat_izi}")
            for k in fiyat_izi:
                print(f"    {'  '*derinlik}   {k} = {veri[k]}")
        # ic listeye in
        for k in ("content", "products", "data", "items", "productList",
                  "result", "results", "categories"):
            if k in veri and veri[k]:
                print(f"    {'  '*derinlik}'{k}' icine iniliyor...")
                incele(veri[k], derinlik + 1)
                return
    elif isinstance(veri, list):
        print(f"    {'  '*derinlik}liste {len(veri)} oge")
        if veri:
            incele(veri[0], derinlik + 1)


for ad, url, ref in HEDEFLER:
    dene(ad, url, ref)

print(f"\n{'='*60}")
print("JSON donen + fiyat alani olan uclar kullanilabilir.")
print("Indirim alani da varsa ana listeye, sadece fiyatsa karsilastirmaya.")
