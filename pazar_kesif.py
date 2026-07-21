"""
UCUZCUM — YENI MARKET KESIF ARACI

Ne yapar:
  Aday market sitelerine tek tek bakar ve su sorulari cevaplar:
    - Site aciliyor mu, yoksa bot engeli mi var (403/503/Cloudflare)?
    - Sayfada yapisal veri var mi (__NEXT_DATA__, JSON-LD, apollo state)?
    - HTML icinde api adresleri geciyor mu?
    - Fiyat kaliplari HTML'de goruluyor mu?

Amac: hangi marketin eklenebilir oldugunu tahminle degil olcumle secmek.

KULLANIM (Colab):
  1) Bu dosyayi GitHub'daki 'ucuzcum-web' deposuna yukle
  2) Colab'da bir hucreye:
       !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/pazar_kesif.py -o p.py
  3) Baska bir hucreye:
       exec(open('p.py').read())
"""

import json
import re
import urllib.error
import urllib.request

BASLIK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

ADAYLAR = [
    ("SOK",            "https://www.sokmarket.com.tr/"),
    ("SOK kampanya",   "https://www.sokmarket.com.tr/kampanyali-urunler"),
    ("CarrefourSA",    "https://www.carrefoursa.com/"),
    ("CarrefourSA ind","https://www.carrefoursa.com/indirimli-urunler/c/1150"),
    ("Tarim Kredi",    "https://www.tarimkredimarket.com.tr/"),
    ("Hakmar Express", "https://www.hakmarexpress.com.tr/"),
    ("Onur Market",    "https://www.onurmarket.com/"),
    ("Happy Center",   "https://www.happycenter.com.tr/"),
    ("Ozdilek",        "https://www.ozdilekteyim.com/"),
    ("Metro",          "https://www.metro-tr.com/"),
]


def getir(adres, sure=15):
    istek = urllib.request.Request(adres, headers=BASLIK)
    try:
        with urllib.request.urlopen(istek, timeout=sure) as cevap:
            ham = cevap.read()
            try:
                metin = ham.decode("utf-8")
            except UnicodeDecodeError:
                metin = ham.decode("iso-8859-9", "ignore")
            return cevap.status, metin
    except urllib.error.HTTPError as h:
        return h.code, ""
    except Exception as e:
        return f"HATA:{type(e).__name__}", ""


def incele(ad, adres):
    kod, html = getir(adres)
    print(f"\n{'='*60}")
    print(f"{ad}  ->  {adres}")
    print(f"  durum: {kod}   uzunluk: {len(html)}")

    if not html:
        print("  SONUC: icerik alinamadi (engel ya da hata)")
        return

    dusuk = html.lower()

    # bot engeli isaretleri
    engeller = []
    for anahtar, etiket in [
        ("cloudflare", "Cloudflare"),
        ("captcha", "CAPTCHA"),
        ("access denied", "erisim reddi"),
        ("datadome", "DataDome"),
        ("incapsula", "Imperva"),
        ("just a moment", "Cloudflare bekleme"),
    ]:
        if anahtar in dusuk:
            engeller.append(etiket)
    if engeller:
        print(f"  ENGEL isareti: {', '.join(engeller)}")

    # yapisal veri
    bulgular = []
    if "__NEXT_DATA__" in html:
        bulgular.append("__NEXT_DATA__ (Next.js - veri gomulu)")
    if "application/ld+json" in dusuk:
        bulgular.append("JSON-LD")
    if "__APOLLO_STATE__" in html or "apolloState" in html:
        bulgular.append("Apollo/GraphQL")
    if "window.__INITIAL_STATE__" in html or "__NUXT__" in html:
        bulgular.append("gomulu baslangic durumu")
    print(f"  yapisal veri: {', '.join(bulgular) if bulgular else 'yok'}")

    # api adresleri
    apiler = set()
    for kalip in [r'https?://[a-z0-9.\-]*api[a-z0-9.\-/]*',
                  r'"/api/[a-zA-Z0-9/_\-]+',
                  r'https?://[a-z0-9.\-]+/rest/[a-zA-Z0-9/_\-]+']:
        for bulunan in re.findall(kalip, html, re.I)[:40]:
            temiz = bulunan.strip('"').rstrip('/')
            if 3 < len(temiz) < 90:
                apiler.add(temiz)
    if apiler:
        print("  api izleri:")
        for a in sorted(apiler)[:8]:
            print(f"    {a}")
    else:
        print("  api izleri: yok")

    # fiyat kalibi
    fiyatlar = re.findall(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", html)
    print(f"  HTML'de gorulen fiyat sayisi: {len(fiyatlar)}"
          + (f"  ornek: {fiyatlar[:3]}" if fiyatlar else ""))

    # ozet yorum
    if engeller and not bulgular:
        yorum = "ZOR - bot engeli var, yapisal veri yok"
    elif bulgular and fiyatlar:
        yorum = "UMUT VAR - hem yapisal veri hem fiyat goruluyor"
    elif bulgular:
        yorum = "INCELENEBILIR - yapisal veri var, fiyat ic sayfalarda olabilir"
    elif fiyatlar:
        yorum = "ORTA - fiyat var ama HTML ayiklamak gerekir"
    else:
        yorum = "ZAYIF - ne yapisal veri ne fiyat"
    print(f"  >> {yorum}")


def calis():
    print("MARKET KESIF TARAMASI")
    print("Her site icin: engel var mi, yapisal veri var mi, fiyat goruluyor mu")
    for ad, adres in ADAYLAR:
        try:
            incele(ad, adres)
        except Exception as e:
            print(f"\n{ad}: beklenmeyen hata {type(e).__name__}")
    print(f"\n{'='*60}")
    print("Tarama bitti. 'UMUT VAR' ve 'INCELENEBILIR' olanlari konusalim.")


calis()
