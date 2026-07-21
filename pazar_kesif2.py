"""
UCUZCUM — KESIF 2. ASAMA

Birinci taramada umut veren siteleri derinlemesine inceler:
  - Ana sayfadaki ic baglantilardan kampanya/indirim/urun sayfalarini bulur
  - Bu sayfalari acip JSON-LD urun verisi, fiyat kalibi ve api izi arar
  - Ozdilek icin api.ozdilekteyim.com uzerinde yaygin uc noktalari dener

KULLANIM (Colab):
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/pazar_kesif2.py -o p2.py
  exec(open('p2.py').read())
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

BASLIK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

HEDEFLER = [
    ("Hakmar Express", "https://www.hakmarexpress.com.tr/"),
    ("Happy Center",   "https://www.happycenter.com.tr/"),
    ("SOK",            "https://www.sokmarket.com.tr/"),
    ("Ozdilek",        "https://www.ozdilekteyim.com/"),
]

ANAHTARLAR = ["kampanya", "indirim", "firsat", "aktuel", "katalog",
              "urun", "market", "brosur", "haftanin"]


def getir(adres, sure=15):
    istek = urllib.request.Request(adres, headers=BASLIK)
    try:
        with urllib.request.urlopen(istek, timeout=sure) as cevap:
            ham = cevap.read()
            try:
                return cevap.status, ham.decode("utf-8")
            except UnicodeDecodeError:
                return cevap.status, ham.decode("iso-8859-9", "ignore")
    except urllib.error.HTTPError as h:
        return h.code, ""
    except Exception as e:
        return f"HATA:{type(e).__name__}", ""


def ic_baglantilar(html, temel):
    """Sayfadaki ilgili ic baglantilari toplar."""
    bulunan = re.findall(r'href="([^"]+)"', html)
    sonuc, gorulen = [], set()
    for yol in bulunan:
        dusuk = yol.lower()
        if not any(a in dusuk for a in ANAHTARLAR):
            continue
        if dusuk.startswith("http") and urllib.parse.urlparse(temel).netloc \
                not in dusuk:
            continue
        tam = urllib.parse.urljoin(temel, yol)
        if tam in gorulen:
            continue
        gorulen.add(tam)
        sonuc.append(tam)
        if len(sonuc) >= 6:
            break
    return sonuc


def jsonld_urunler(html):
    """JSON-LD bloklarindaki urun sayisini ve ornek adi dondurur."""
    bloklar = re.findall(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
        html, re.S | re.I)
    urun_sayisi, ornek = 0, None
    for blok in bloklar:
        try:
            veri = json.loads(blok.strip())
        except Exception:
            continue
        yigin = veri if isinstance(veri, list) else [veri]
        while yigin:
            oge = yigin.pop()
            if isinstance(oge, list):
                yigin.extend(oge)
                continue
            if not isinstance(oge, dict):
                continue
            tur = str(oge.get("@type", ""))
            if "Product" in tur:
                urun_sayisi += 1
                if not ornek:
                    ornek = oge.get("name")
            for deger in oge.values():
                if isinstance(deger, (dict, list)):
                    yigin.append(deger)
    return urun_sayisi, ornek


def sayfa_incele(adres, girinti="    "):
    kod, html = getir(adres)
    if not html:
        print(f"{girinti}{adres[:70]}  -> durum {kod}, icerik yok")
        return
    urun, ornek = jsonld_urunler(html)
    fiyatlar = re.findall(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", html)
    print(f"{girinti}{adres[:70]}")
    print(f"{girinti}  durum {kod} | uzunluk {len(html)} | "
          f"JSON-LD urun: {urun} | fiyat: {len(fiyatlar)}")
    if ornek:
        print(f"{girinti}  ornek urun: {str(ornek)[:55]}")
    if fiyatlar:
        print(f"{girinti}  ornek fiyat: {fiyatlar[:3]}")

    apiler = set()
    for kalip in [r'"/api/[a-zA-Z0-9/_\-]{3,40}',
                  r'https?://[a-z0-9.\-]+/api/[a-zA-Z0-9/_\-]{3,40}',
                  r'https?://api\.[a-z0-9.\-]+[a-zA-Z0-9/_\-]{0,40}']:
        for bulunan in re.findall(kalip, html, re.I)[:30]:
            temiz = bulunan.strip('"')
            if "whatsapp" in temiz or "google" in temiz or "insider" in temiz:
                continue
            apiler.add(temiz)
    if apiler:
        print(f"{girinti}  api izleri:")
        for a in sorted(apiler)[:6]:
            print(f"{girinti}    {a}")


def ozdilek_api_dene():
    print("\n" + "=" * 62)
    print("OZDILEK API DENEMESI")
    yollar = [
        "https://api.ozdilekteyim.com/api/v1/products",
        "https://api.ozdilekteyim.com/api/products",
        "https://api.ozdilekteyim.com/v1/products",
        "https://api.ozdilekteyim.com/api/v1/categories",
        "https://api.ozdilekteyim.com/api/v1/campaigns",
    ]
    for yol in yollar:
        kod, icerik = getir(yol, sure=10)
        ozet = ""
        if icerik:
            kirp = icerik.strip()[:110].replace("\n", " ")
            ozet = f" | {kirp}"
        print(f"  {kod}  {yol}{ozet}")


def calis():
    print("KESIF 2. ASAMA — ic sayfa incelemesi\n")
    for ad, temel in HEDEFLER:
        print("=" * 62)
        print(f"{ad}  ({temel})")
        kod, html = getir(temel)
        if not html:
            print(f"  ana sayfa alinamadi (durum {kod})")
            continue

        urun, ornek = jsonld_urunler(html)
        print(f"  ana sayfa: JSON-LD urun {urun}"
              + (f" | ornek: {str(ornek)[:40]}" if ornek else ""))

        baglantilar = ic_baglantilar(html, temel)
        if not baglantilar:
            print("  ilgili ic baglanti bulunamadi")
            continue
        print(f"  incelenecek {len(baglantilar)} sayfa:")
        for b in baglantilar:
            try:
                sayfa_incele(b)
            except Exception as e:
                print(f"    {b[:60]} -> hata {type(e).__name__}")

    ozdilek_api_dene()
    print("\n" + "=" * 62)
    print("Bitti. JSON-LD urun sayisi yuksek ya da api cevap veren yerler")
    print("eklenebilir demektir.")


calis()
