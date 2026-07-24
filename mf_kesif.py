"""
UCUZCUM — marketfiyati.org.tr API KESIF

Bu API cok sayida market zincirini tek yerde topluyor olabilir.
Olcecegimiz seyler:
  - API cevap veriyor mu, hangi yapida?
  - Bir urunde HANGI marketler + fiyatlar donuyor?
  - Indirim / eski fiyat alani var mi (bizim modelimiz icin sart)?
  - Indirimli urunleri TOPLU listeleyebiliyor muyuz, yoksa sadece arama mi?

KULLANIM (Colab):
  Bu dosyayi ucuzcum-web'e yukle, sonra:
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/mf_kesif.py -o mf.py
  exec(open('mf.py').read())
"""

import json
import urllib.error
import urllib.request

TEMEL = "https://api.marketfiyati.org.tr/api/v3"
BASLIK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://marketfiyati.org.tr",
    "Referer": "https://marketfiyati.org.tr/",
}


def post(yol, govde):
    adres = f"{TEMEL}/{yol}"
    veri = json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(adres, data=veri, headers=BASLIK, method="POST")
    try:
        with urllib.request.urlopen(istek, timeout=20) as c:
            return c.status, json.loads(c.read().decode("utf-8"))
    except urllib.error.HTTPError as h:
        govde = ""
        try:
            govde = h.read().decode("utf-8")[:200]
        except Exception:
            pass
        return h.code, govde
    except Exception as e:
        return f"HATA:{type(e).__name__}", str(e)[:200]


def get(yol):
    adres = f"{TEMEL}/{yol}"
    istek = urllib.request.Request(adres, headers=BASLIK)
    try:
        with urllib.request.urlopen(istek, timeout=20) as c:
            return c.status, json.loads(c.read().decode("utf-8"))
    except urllib.error.HTTPError as h:
        return h.code, ""
    except Exception as e:
        return f"HATA:{type(e).__name__}", str(e)[:150]


def anahtarlari_yaz(veri, girinti="    "):
    if isinstance(veri, dict):
        print(f"{girinti}anahtarlar: {list(veri.keys())}")
    elif isinstance(veri, list):
        print(f"{girinti}liste, {len(veri)} oge")
        if veri:
            anahtarlari_yaz(veri[0], girinti + "  ")


def kesif():
    print("=" * 62)
    print("1) ARAMA DENEMESI (searchByText)")
    for yol, govde in [
        ("search", {"keywords": "sut", "pages": 0, "size": 5,
                    "menuType": "articles"}),
        ("searchByText", {"keywords": "sut", "pages": 0, "size": 5}),
        ("search", {"keywords": "sut"}),
    ]:
        kod, cevap = post(yol, govde)
        print(f"\n  POST {yol}  govde={json.dumps(govde, ensure_ascii=False)}")
        print(f"    durum: {kod}")
        if isinstance(cevap, dict):
            anahtarlari_yaz(cevap)
            # ic yapiyi ac
            for ana in ("content", "products", "data", "items"):
                if ana in cevap and cevap[ana]:
                    print(f"    '{ana}' icinde ilk oge:")
                    ilk = cevap[ana][0] if isinstance(cevap[ana], list) else cevap[ana]
                    print(f"      {json.dumps(ilk, ensure_ascii=False)[:600]}")
                    break
        else:
            print(f"    cevap: {str(cevap)[:200]}")

    print("\n" + "=" * 62)
    print("2) KATEGORI DENEMESI (searchByCategories)")
    for govde in [
        {"categories": ["indirimli"], "pages": 0, "size": 5},
        {"keywords": "", "pages": 0, "size": 5, "menuType": "articles"},
        {"pages": 0, "size": 5},
    ]:
        kod, cevap = post("searchByCategories", govde)
        print(f"\n  POST searchByCategories  {json.dumps(govde, ensure_ascii=False)}")
        print(f"    durum: {kod}")
        if isinstance(cevap, dict):
            anahtarlari_yaz(cevap)
        else:
            print(f"    cevap: {str(cevap)[:200]}")

    print("\n" + "=" * 62)
    print("3) FIYAT/INDIRIM ALANI VAR MI? (bir urunun tam yapisi)")
    kod, cevap = post("search", {"keywords": "nutella", "pages": 0, "size": 3})
    if isinstance(cevap, dict):
        icerik = cevap.get("content") or cevap.get("products") or []
        if icerik:
            urun = icerik[0]
            print(f"  URUN: {json.dumps(urun, ensure_ascii=False)[:1500]}")
            # market listesi var mi?
            for ana in ("productDepotInfoList", "depotInfoList", "prices",
                        "marketPrices", "depots"):
                if ana in urun:
                    print(f"\n  '{ana}' -> {len(urun[ana])} market")
                    if urun[ana]:
                        print(f"    ilk market: "
                              f"{json.dumps(urun[ana][0], ensure_ascii=False)[:400]}")


kesif()
print("\n" + "=" * 62)
print("Bakilacak: market listesi + eski/indirim fiyat alani var mi,")
print("ve indirimli urunler toplu cekilebiliyor mu.")
