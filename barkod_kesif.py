# -*- coding: utf-8 -*-
"""
UCUZCUM — BARKOD KESFI
Marketlerin uclarinda barkod (EAN/GTIN) alani var mi?
Colab'da calistir, ciktiyi gonder.
"""
import json, urllib.request, re

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

def getir(url, ek=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if ek: h.update(ek)
    try:
        r = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(r, timeout=25) as c:
            return json.loads(c.read().decode("utf-8"))
    except Exception as e:
        print("   hata:", type(e).__name__, str(e)[:60])
        return None

def barkod_ara(nesne, yol=""):
    """Ic ice sozlukte barkoda benzeyen alanlari bulur."""
    bulunan = []
    if isinstance(nesne, dict):
        for a, b in nesne.items():
            yeni = f"{yol}.{a}" if yol else a
            dusuk = a.lower()
            if any(x in dusuk for x in ("barcode", "barkod", "ean", "gtin", "upc")):
                bulunan.append((yeni, str(b)[:60]))
            bulunan += barkod_ara(b, yeni)
    elif isinstance(nesne, list) and nesne:
        bulunan += barkod_ara(nesne[0], yol + "[0]")
    return bulunan

print("=" * 60)
print("1) A101")
d = getir("https://www.a101.com.tr/api/v1/pwa/products?page=1&limit=3")
if d:
    print("   ust anahtarlar:", list(d)[:8])
    for y, v in barkod_ara(d)[:10]:
        print(f"   {y} = {v}")
else:
    print("   alinamadi (uc degismis olabilir)")

print("\n" + "=" * 60)
print("2) OZDILEK")
d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
          "/products/search?query=sut&pageSize=2&currentPage=0&lang=tr&curr=TRY",
          {"Referer": "https://www.ozdilekteyim.com/",
           "Origin": "https://www.ozdilekteyim.com"})
if d and d.get("products"):
    u = d["products"][0]
    print("   urun anahtarlari:", list(u)[:14])
    b = barkod_ara(u)
    print("   barkod alani:", b if b else "YOK")

print("\n" + "=" * 60)
print("3) MIGROS (detay ucu)")
d = getir("https://www.migros.com.tr/rest/products/search?q=sut")
liste = (d or {}).get("data", {}).get("storeProductInfos", [])
if liste:
    sku = liste[0].get("sku")
    print("   ornek sku:", sku)
    detay = getir(f"https://www.migros.com.tr/rest/products/screens/{sku}")
    dto = (detay or {}).get("data", {}).get("storeProductInfoDTO") or {}
    print("   detay anahtar sayisi:", len(dto))
    b = barkod_ara(dto)
    print("   barkod alani:", b if b else "YOK")

print("\n" + "=" * 60)
print("4) MACROCENTER")
d = getir("https://www.macrocenter.com.tr/rest/products/search?q=sut")
liste = (d or {}).get("data", {}).get("storeProductInfos", [])
if liste:
    b = barkod_ara(liste[0])
    print("   barkod alani:", b if b else "YOK")
    print("   urun anahtarlari:", list(liste[0])[:14])

print("\nBitti. Ciktinin TAMAMINI gonder.")
