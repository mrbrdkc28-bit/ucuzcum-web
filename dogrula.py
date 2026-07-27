"""
UCUZCUM — ESLESME DOGRULAMA (kuru calisma)

Tablodaki elle eslesmeleri ORNEKLEM uzerinde test eder.
Firebase'e HICBIR SEY YAZMAZ. Botun yaptigi isin aynisini yapip
sonucu ekrana basar.

Her eslesme icin bakar:
  - Kaydedilen kod hala gecerli mi (urun bulunuyor mu)?
  - Gramaj tutuyor mu?
  - Fiyat makul mu (bizim fiyatin 0.33x - 3x araligi)?

KULLANIM (Colab):
  1) eslesmeler.json Colab'da olsun
  2) !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/dogrula.py -o d.py
  3) exec(open('d.py').read())
"""

import glob
import json
import random
import re
import time
import urllib.parse
import urllib.request

FB = "https://ucuzum-4e82f-default-rtdb.firebaseio.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ORNEKLEM = 30          # kac eslesme test edilsin


def tr_ara(s):
    s = (s or "").lower()
    for a, b in zip("ışğüöçâîé", "isguocaie"):
        s = s.replace(a, b)
    return s


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", " ", tr_ara(s))


def miktar(ad):
    metin = re.sub(r"[^a-z0-9,.x* ]", " ", tr_ara(ad))
    coklu = re.search(r"(\d+)\s*[x*]\s*(\d+[.,]?\d*)\s*(kg|gr|g|ml|lt|l|cl)\b",
                      metin)
    if coklu:
        try:
            return (round(int(coklu.group(1))
                          * float(coklu.group(2).replace(",", "."))), "x")
        except ValueError:
            return None
    bulunan = re.findall(r"(\d+[.,]?\d*)\s*(kg|gr|g|ml|lt|l|cl)\b", metin)
    if bulunan:
        sayi, birim = bulunan[-1]
        try:
            d = float(sayi.replace(",", "."))
        except ValueError:
            return None
        if birim == "kg":
            d, birim = d * 1000, "g"
        elif birim == "gr":
            birim = "g"
        elif birim in ("lt", "l"):
            d, birim = d * 1000, "ml"
        elif birim == "cl":
            d, birim = d * 10, "ml"
        return (round(d), birim)
    adet = re.search(r"\b(\d+)\s*(?:li|lu|lı|lü)\b", metin)
    if adet:
        return (int(adet.group(1)), "adet")
    return None


def mk(m):
    return f"{m[0]} {m[1]}" if m else "?"


def getir(url, baslik=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if baslik:
        h.update(baslik)
    try:
        r = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(r, timeout=15) as c:
            return json.loads(c.read().decode("utf-8"))
    except Exception:
        return None


def satis_fiyati(dto):
    reg = dto.get("regularPrice") or 0
    shown = dto.get("shownPrice") or 0
    if shown and (not reg or shown <= reg):
        return shown
    return reg


# ---- market bazli "kod ile fiyat getir" (botun yaptiginin aynisi) ----

def migros_getir(kod, ad):
    d = getir(f"https://www.migros.com.tr/rest/products/screens/{kod}")
    dto = (d or {}).get("data", {}).get("storeProductInfoDTO") or {}
    f = satis_fiyati(dto)
    if not f:
        return None
    return {"ad": dto.get("name", ""), "fiyat": round(f / 100, 2)}


def macro_getir(kod, ad):
    d = getir("https://www.macrocenter.com.tr/rest/products/search?q="
              + urllib.parse.quote(ad))
    for s in (d or {}).get("data", {}).get("storeProductInfos", [])[:8]:
        if str(s.get("sku") or s.get("id")) != str(kod):
            continue
        f = satis_fiyati(s)
        if not f:
            return None
        return {"ad": s.get("name", ""), "fiyat": round(f / 100, 2)}
    return None


def ozdilek_getir(kod, ad):
    d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
              "/products/search?query=" + urllib.parse.quote(ad)
              + "&pageSize=8&currentPage=0&lang=tr&curr=TRY",
              {"Referer": "https://www.ozdilekteyim.com/",
               "Origin": "https://www.ozdilekteyim.com"})
    for u in (d or {}).get("products", [])[:8]:
        if str(u.get("code")) != str(kod):
            continue
        f = ((u.get("price") or {}).get("value")
             or (u.get("listPrice") or {}).get("value"))
        if not f:
            return None
        return {"ad": u.get("name", ""), "fiyat": round(float(f), 2)}
    return None


GETIR = {"migros": migros_getir, "ozdilek": ozdilek_getir,
         "macro": macro_getir}
ETIKET = {"migros": "Migros", "ozdilek": "Ozdilek", "macro": "Macrocenter"}


def calis():
    dosyalar = sorted(glob.glob("eslesmeler*.json"))
    if not dosyalar:
        print("eslesmeler.json bulunamadi.")
        return
    tablo = json.load(open(dosyalar[-1]))
    urunler = getir(FB + "/urunler.json") or {}
    print(f"Tablo: {dosyalar[-1]} ({len(tablo)} kayit) | "
          f"Firebase: {len(urunler)} urun\n")

    # test edilecek (urun_id, market) ciftleri
    ciftler = []
    for uid, kayit in tablo.items():
        if not isinstance(kayit, dict) or kayit.get("atla"):
            continue
        if uid not in urunler:
            continue
        for m in ("migros", "ozdilek", "macro"):
            esl = kayit.get(m)
            if isinstance(esl, dict) and esl.get("kod"):
                ciftler.append((uid, m, esl))

    print(f"Elle eslesme sayisi: {len(ciftler)}")
    if not ciftler:
        print("Test edilecek elle eslesme yok.")
        return

    ornek = random.sample(ciftler, min(ORNEKLEM, len(ciftler)))
    print(f"Ornek {len(ornek)} tanesi test ediliyor...\n")

    ok = bulunamadi = gramaj_hata = fiyat_hata = 0
    for uid, market, esl in ornek:
        urun = urunler[uid]
        ad = urun.get("urun_adi", "")
        bizim = urun.get("gecerli_fiyat", 0)
        hedef_m = miktar(ad)

        sonuc = GETIR[market](esl["kod"], esl.get("ad", ad))
        time.sleep(0.25)

        if not sonuc:
            bulunamadi += 1
            print(f"  [BULUNAMADI] {ETIKET[market]:12} {ad[:40]}")
            print(f"               kod {esl['kod']} karsilik vermedi")
            continue

        m_yeni = miktar(sonuc["ad"])
        gramaj_ok = (m_yeni == hedef_m)
        oran = (sonuc["fiyat"] / bizim) if bizim else 0
        fiyat_ok = 0.33 <= oran <= 3.0

        if not gramaj_ok:
            gramaj_hata += 1
            durum = "GRAMAJ FARKLI"
        elif not fiyat_ok:
            fiyat_hata += 1
            durum = f"FIYAT SAPIK ({oran:.1f}x)"
        else:
            ok += 1
            durum = "OK"

        print(f"  [{durum}] {ETIKET[market]}")
        print(f"     bizim : {ad[:44]}  {bizim} TL  ({mk(hedef_m)})")
        print(f"     esli  : {sonuc['ad'][:44]}  {sonuc['fiyat']} TL  "
              f"({mk(m_yeni)})")

    n = len(ornek)
    print(f"\n{'='*56}")
    print(f"SONUC ({n} ornek):")
    print(f"  saglam        : {ok}   (%{round(100*ok/n)})")
    print(f"  gramaj farkli : {gramaj_hata}")
    print(f"  fiyat sapik   : {fiyat_hata}")
    print(f"  bulunamadi    : {bulunamadi}")
    print("\nGramaj farkli cikanlari temizle.py toplu duzeltir.")
    print("Bulunamayanlar: urun o markette stoktan kalkmis olabilir,")
    print("bot o turda o marketi karsilastirmaya katmaz (zararsiz).")


calis()
