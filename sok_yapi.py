"""
UCUZCUM — SOK YAPI INCELEMESI

Amac: SOK kampanya sayfasindaki urun verisi ayiklanabilir mi?
Bakilan seyler:
  - Fiyatlarin etrafindaki HTML nasil gorunuyor (ad, gorsel, link bir arada mi?)
  - Sayfada gomulu buyuk JSON blogu var mi (en temiz kaynak)
  - Tekrar eden kap (container) sinif adlari neler

KULLANIM (Colab):
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/sok_yapi.py -o s.py
  exec(open('s.py').read())
"""

import json
import re
import urllib.error
import urllib.request

BASLIK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

SAYFA = "https://www.sokmarket.com.tr/kampanyalar"


def getir(adres, sure=20):
    istek = urllib.request.Request(adres, headers=BASLIK)
    with urllib.request.urlopen(istek, timeout=sure) as cevap:
        return cevap.read().decode("utf-8", "ignore")


def gomulu_json(html):
    """Sayfadaki buyuk JSON bloklarini bulur (en temiz veri kaynagi)."""
    print("\n--- GOMULU JSON ARAMASI ---")
    bulundu = False
    for kalip, etiket in [
        (r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', "__NEXT_DATA__"),
        (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', "__INITIAL_STATE__"),
        (r'window\.__NUXT__\s*=\s*(\{.*?\});', "__NUXT__"),
        (r'self\.__next_f\.push\((.*?)\)', "next_f (RSC)"),
        (r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', "json script"),
    ]:
        for ham in re.findall(kalip, html, re.S)[:3]:
            if len(ham) < 500:
                continue
            bulundu = True
            print(f"  {etiket}: {len(ham)} karakter")
            ipuclari = [a for a in ["price", "fiyat", "product", "urun", "name",
                                    "image", "discount", "indirim"]
                        if a in ham.lower()]
            print(f"    icinde gecen anahtarlar: {ipuclari}")
            print(f"    ilk 200 karakter: {ham[:200]}")
    if not bulundu:
        print("  buyuk gomulu JSON bulunamadi")


def fiyat_cevresi(html, adet=3):
    """Fiyatlarin etrafindaki HTML'i gosterir."""
    print("\n--- FIYAT CEVRESI ---")
    for eslesme in list(re.finditer(r"\d{1,4}[.,]\d{2}\s*(?:TL|₺)", html))[:adet]:
        bas = max(0, eslesme.start() - 700)
        son = min(len(html), eslesme.end() + 250)
        parca = html[bas:son]
        parca = re.sub(r"\s+", " ", parca)
        print(f"\n  >>> {eslesme.group()}")
        print(f"  {parca[:900]}")


def kap_siniflari(html):
    """Tekrar eden sinif adlari - urun kartini isaret eder."""
    print("\n--- TEKRAR EDEN SINIF ADLARI ---")
    siniflar = re.findall(r'class="([^"]{5,80})"', html)
    sayac = {}
    for s in siniflar:
        for tek in s.split():
            if any(a in tek.lower() for a in
                   ["product", "urun", "card", "kart", "price", "fiyat",
                    "item", "list"]):
                sayac[tek] = sayac.get(tek, 0) + 1
    for ad, adet in sorted(sayac.items(), key=lambda x: -x[1])[:15]:
        print(f"  {adet:4}x  {ad}")


def gorsel_ve_link(html):
    """Urun gorseli ve linki nasil duruyor?"""
    print("\n--- GORSEL / LINK ORNEKLERI ---")
    gorseller = re.findall(r'src="([^"]*(?:cdn|image|img|media)[^"]*)"',
                           html, re.I)[:5]
    for g in gorseller:
        print(f"  gorsel: {g[:100]}")
    linkler = re.findall(r'href="(/[^"]*-p[a-z0-9\-]{4,})"', html)[:5]
    for l in linkler:
        print(f"  urun linki: {l[:100]}")


def calis():
    print(f"SOK YAPI INCELEMESI\n{SAYFA}")
    try:
        html = getir(SAYFA)
    except Exception as e:
        print(f"Sayfa alinamadi: {type(e).__name__} {e}")
        return
    print(f"uzunluk: {len(html)}")

    gomulu_json(html)
    kap_siniflari(html)
    gorsel_ve_link(html)
    fiyat_cevresi(html)

    print("\n" + "=" * 60)
    print("Gomulu JSON varsa oradan; yoksa tekrar eden kart sinifindan")
    print("ad + fiyat + gorsel ayiklanabilir mi ona bakacagiz.")


calis()
