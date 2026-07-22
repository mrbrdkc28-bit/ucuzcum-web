"""
UCUZCUM — SOK 2. INCELEME

/kampanyalar sayfasi promosyon kartlari iceriyordu (urun degil).
Bu arac gercek URUN LISTELEME sayfalarini bulup inceler ve
SOK'un olasi API adreslerini yoklar.

KULLANIM (Colab):
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/sok_yapi2.py -o s2.py
  exec(open('s2.py').read())
"""

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

TEMEL = "https://www.sokmarket.com.tr"
BASLANGIC = [TEMEL + "/", TEMEL + "/kampanyalar"]


def getir(adres, sure=20):
    istek = urllib.request.Request(adres, headers=BASLIK)
    try:
        with urllib.request.urlopen(istek, timeout=sure) as cevap:
            return cevap.status, cevap.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as h:
        return h.code, ""
    except Exception as e:
        return f"HATA:{type(e).__name__}", ""


def liste_sayfalari_bul():
    """Urun listeleme gorunumlu baglantilari toplar."""
    adaylar, gorulen = [], set()
    for kaynak in BASLANGIC:
        kod, html = getir(kaynak)
        if not html:
            continue
        for yol in re.findall(r'href="(/[^"]+)"', html):
            if not re.search(r"-(pgrp|sgrp|cgrp)-", yol):
                continue
            tam = urllib.parse.urljoin(TEMEL, yol)
            if tam in gorulen:
                continue
            gorulen.add(tam)
            adaylar.append(tam)
    return adaylar[:8]


def sayfa_analiz(adres):
    kod, html = getir(adres)
    if not html:
        print(f"\n  {adres[:75]}\n    durum {kod}, icerik yok")
        return None

    fiyatlar = re.findall(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", html)
    rsc = html.count("self.__next_f.push")
    print(f"\n  {adres[:75]}")
    print(f"    durum {kod} | uzunluk {len(html)} | fiyat {len(fiyatlar)} "
          f"| RSC parca {rsc}")

    if not fiyatlar:
        print("    -> fiyat yok (icerik tarayicida yukleniyor olabilir)")
        return None

    # urun kartina isaret eden tekrar eden siniflar
    sayac = {}
    for s in re.findall(r'class="([^"]{5,90})"', html):
        for tek in s.split():
            dusuk = tek.lower()
            if any(a in dusuk for a in ["product", "urun", "card", "price",
                                        "fiyat", "item"]):
                sayac[tek] = sayac.get(tek, 0) + 1
    ilk = sorted(sayac.items(), key=lambda x: -x[1])[:6]
    if ilk:
        print("    tekrar eden siniflar:")
        for ad, adet in ilk:
            print(f"      {adet:4}x {ad}")
    return html


def ornek_kart(html):
    """Fiyat cevresinden kisa bir ornek gosterir."""
    eslesme = re.search(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", html)
    if not eslesme:
        return
    bas = max(0, eslesme.start() - 800)
    parca = re.sub(r"\s+", " ", html[bas:eslesme.end() + 150])
    print("\n  --- ORNEK KART ---")
    print(f"  {parca[:850]}")


def api_dene():
    print("\n" + "=" * 62)
    print("SOK API DENEMESI")
    yollar = [
        "https://api.ceptesok.com/api/v1/products",
        "https://api.ceptesok.com/api/v1/campaigns",
        "https://api.ceptesok.com/v1/products",
        "https://www.sokmarket.com.tr/api/products",
        "https://www.sokmarket.com.tr/api/v1/products",
        "https://www.sokmarket.com.tr/_next/data",
    ]
    for yol in yollar:
        kod, icerik = getir(yol, sure=10)
        ozet = ""
        if icerik:
            ozet = " | " + re.sub(r"\s+", " ", icerik.strip()[:100])
        print(f"  {kod}  {yol}{ozet}")


def calis():
    print("SOK 2. INCELEME — urun listeleme sayfalari\n")
    adaylar = liste_sayfalari_bul()
    if not adaylar:
        print("Listeleme sayfasi bulunamadi.")
    else:
        print(f"{len(adaylar)} aday sayfa bulundu")

    dolu = None
    for adres in adaylar:
        html = sayfa_analiz(adres)
        if html and dolu is None:
            dolu = html

    if dolu:
        ornek_kart(dolu)
    else:
        print("\nHicbir sayfada sunucudan gelen fiyat bulunamadi.")

    api_dene()
    print("\n" + "=" * 62)
    print("Urun karti icinde ad + eski fiyat + yeni fiyat birlikte")
    print("goruluyorsa SOK eklenebilir demektir.")


calis()
