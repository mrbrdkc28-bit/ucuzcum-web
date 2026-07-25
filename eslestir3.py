"""
UCUZCUM — ESLESTIRME ARACI (v3, basit)

Her market icin AYRI AYRI soruyor. Tek tusa basiyorsun, bitiyor.
Sonuc yoksa hic sormuyor, gecip gidiyor.

TUSLAR (her soruda gecerli):
  1..6   -> o numarali urunu sec
  0      -> bu markette yok, gec        (Enter de ayni is)
  a      -> bu urun hicbir yerde eslenemez, bir daha sorma
  g      -> bu turden TUM urunleri atla (sucuk, salam vb.)
  b      -> bitir ve dosyayi indir

KULLANIM (Colab):
  1) eslesmeler.json'i Colab'a yukle
  2) !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/eslestir3.py -o e3.py
  3) exec(open('e3.py').read())
"""

import glob
import json
import re
import time
import urllib.parse
import urllib.request

FB = "https://ucuzum-4e82f-default-rtdb.firebaseio.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
CIKTI = "eslesmeler.json"


# ---------------------------------------------------------------- yardimcilar

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


def miktar_yazi(m):
    return f"{m[0]} {m[1]}" if m else "?"


def anahtar_kelimeler(ad, n=4):
    dur = {"ve", "ile", "gr", "kg", "ml", "adet", "paket"}
    return [w for w in normalize(ad).split()
            if len(w) >= 3 and not w.isdigit() and w not in dur][:n]


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


# ---------------------------------------------------------------- aramalar

def migros_ara(sorgu):
    d = getir("https://www.migros.com.tr/rest/products/search?q="
              + urllib.parse.quote(sorgu))
    if not d:
        return []
    out = []
    for u in d.get("data", {}).get("storeProductInfos", [])[:6]:
        sku, f = (u.get("sku") or u.get("id")), (u.get("regularPrice") or 0)
        if sku and f:
            out.append({"kod": str(sku), "ad": u.get("name", ""),
                        "fiyat": round(f / 100, 2)})
    return out


def ozdilek_ara(sorgu):
    d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
              "/products/search?query=" + urllib.parse.quote(sorgu)
              + "&pageSize=6&currentPage=0&lang=tr&curr=TRY",
              {"Referer": "https://www.ozdilekteyim.com/",
               "Origin": "https://www.ozdilekteyim.com"})
    if not d:
        return []
    out = []
    for u in d.get("products", [])[:6]:
        kod = u.get("code")
        deger = ((u.get("listPrice") or {}).get("value")
                 or (u.get("price") or {}).get("value"))
        if kod and deger:
            out.append({"kod": str(kod), "ad": u.get("name", ""),
                        "fiyat": round(float(deger), 2)})
    return out


def macro_ara(sorgu):
    d = getir("https://www.macrocenter.com.tr/rest/products/search?q="
              + urllib.parse.quote(sorgu))
    if not d:
        return []
    out = []
    for u in d.get("data", {}).get("storeProductInfos", [])[:6]:
        sku, f = (u.get("sku") or u.get("id")), (u.get("regularPrice") or 0)
        if sku and f:
            out.append({"kod": str(sku), "ad": u.get("name", ""),
                        "fiyat": round(f / 100, 2)})
    return out


MARKETLER = [("migros", "MIGROS", migros_ara),
             ("ozdilek", "OZDILEK", ozdilek_ara),
             ("macro", "MACROCENTER", macro_ara)]


# ---------------------------------------------------------------- tablo

def tablo_yukle():
    dosyalar = sorted(glob.glob("eslesmeler*.json"))
    if not dosyalar:
        print("!! eslesmeler.json bulunamadi. Once dosyayi Colab'a yukle,")
        print("   yoksa mevcut 188 eslesmen kaybolur. Duruyorum.\n")
        return None
    ham = json.load(open(dosyalar[-1]))
    print(f"Tablo yuklendi: {dosyalar[-1]}  ({len(ham)} kayit)")
    yeni, cevrilen = {}, 0
    for k, v in ham.items():
        if not isinstance(v, dict):
            continue
        if v.get("atla"):
            yeni[k] = {"atla": True}
            continue
        kayit = {}
        if v.get("sku"):
            kayit["migros"] = {"kod": str(v["sku"]), "ad": v.get("ad", ""),
                               "carpan": v.get("carpan")}
            cevrilen += 1
        for m in ("migros", "ozdilek", "macro"):
            if isinstance(v.get(m), dict):
                kayit[m] = v[m]
        if kayit:
            yeni[k] = kayit
    if cevrilen:
        print(f"  {cevrilen} Migros eslesmesi korundu")
    return yeni


def tablo_kaydet(tablo):
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(tablo, f, ensure_ascii=False, indent=1)
    esl = sum(1 for v in tablo.values() if not v.get("atla"))
    atl = sum(1 for v in tablo.values() if v.get("atla"))
    print(f"\n{CIKTI} yazildi — {esl} eslesme, {atl} atlanan")
    try:
        from google.colab import files
        files.download(CIKTI)
        print("Indi. 'ucuzcum-bot' deposuna yukle (eskisinin ustune).")
    except Exception:
        pass


# ---------------------------------------------------------------- ana dongu

class Bitti(Exception):
    pass


def soru(baslik, adaylar, hedef_m):
    """Tek market icin secim sorar. Donus: secilen aday | None"""
    print(f"\n{baslik}:")
    if not adaylar:
        print("   sonuc yok — gecildi")
        return None
    for n, s in enumerate(adaylar, 1):
        m = miktar(s["ad"])
        isaret = "   << ayni miktar" if (m and m == hedef_m) else ""
        print(f"   {n}) {s['ad'][:50]:52} {s['fiyat']} TL{isaret}")
    while True:
        c = input(f"{baslik} secimi (1-{len(adaylar)} / 0=yok): ").strip().lower()
        if c in ("b",):
            raise Bitti("bitir")
        if c in ("a", "g"):
            raise Bitti(c)
        if c in ("", "0"):
            return None
        if c.isdigit() and 1 <= int(c) <= len(adaylar):
            return adaylar[int(c) - 1]
        print("   ge\u00e7ersiz. numara ya da 0 yaz.")


def calis():
    tablo = tablo_yukle()
    if tablo is None:
        return

    urunler = getir(FB + "/urunler.json") or {}
    hedefler = []
    for k, v in urunler.items():
        if not isinstance(v, dict):
            continue
        kayit = tablo.get(k, {})
        if kayit.get("atla"):
            continue
        ad = v.get("urun_adi", "")
        if not anahtar_kelimeler(ad):
            continue
        eksik = [m for m, _, _ in MARKETLER
                 if m not in kayit and v.get("market", "").lower() != m]
        if eksik:
            hedefler.append((k, v))
    hedefler.sort(key=lambda x: normalize(x[1].get("urun_adi", "")))

    print(f"\nEslenecek urun: {len(hedefler)}")
    print("Tuslar:  numara=sec   0/Enter=yok   a=urunu atla   "
          "g=grubu atla   b=bitir\n")

    atlanan_gruplar = set()
    sayac = 0
    for urun_id, v in hedefler:
        sayac += 1
        ad = v.get("urun_adi", "")
        kel = anahtar_kelimeler(ad)
        if kel and kel[0] in atlanan_gruplar:
            tablo[urun_id] = {"atla": True}
            continue

        kayit = dict(tablo.get(urun_id, {}))
        hedef_m = miktar(ad)
        print("=" * 64)
        print(f"[{sayac}/{len(hedefler)}]  {ad}")
        print(f"   {v.get('market','')}  {v.get('gecerli_fiyat','')} TL"
              f"   miktar: {miktar_yazi(hedef_m)}")

        sorgu = " ".join(kel)
        try:
            for kod, baslik, ara in MARKETLER:
                if v.get("market", "").lower() == kod:
                    continue                      # kendi marketi
                if kod in kayit:
                    print(f"\n{baslik}: zaten esli "
                          f"({kayit[kod].get('ad','')[:40]})")
                    continue
                secilen = soru(baslik, ara(sorgu), hedef_m)
                if secilen:
                    kayit[kod] = {"kod": secilen["kod"], "ad": secilen["ad"]}
                time.sleep(0.2)
        except Bitti as e:
            if str(e) == "bitir":
                break
            if str(e) == "a":
                tablo[urun_id] = {"atla": True}
                print("   -> bu urun bir daha sorulmayacak")
                continue
            if str(e) == "g":
                if kel:
                    atlanan_gruplar.add(kel[0])
                    print(f"   -> '{kel[0]}' iceren tum urunler atlanacak")
                tablo[urun_id] = {"atla": True}
                continue

        if kayit:
            tablo[urun_id] = kayit
            bulunan = [m for m in ("migros", "ozdilek", "macro") if m in kayit]
            if bulunan:
                print(f"   kaydedildi: {', '.join(bulunan)}")

    tablo_kaydet(tablo)


calis()
