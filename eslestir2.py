"""
UCUZCUM — COK MARKETLI ESLESTIRME ARACI (v2)

Bir urunu ayni anda MIGROS + OZDILEK + MACROCENTER'a esler.
Eski eslesmeler.json (sadece Migros) otomatik yeni bicime cevrilir,
188 eslesmen KAYBOLMAZ.

TUSLAR (tek satirda, bosluk ayirarak):
  1 2 0   -> Migros=1, Ozdilek=2, Macrocenter=atla
  1       -> sadece Migros=1, digerleri atlanir
  Enter   -> bu urunu gec (mevcut eslesmeler korunur)
  a       -> bu urunu KALICI atla (bir daha sorulmaz)
  g       -> bu urunle ayni tur tum urunleri KALICI atla (sucuk, salam vb.)
  b       -> bitir, dosyayi indir

KULLANIM (Colab):
  1) eslesmeler.json'i Colab'a yukle (ucuzcum-bot deposundan indir)
  2) !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/eslestir2.py -o e2.py
  3) exec(open('e2.py').read())
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
    """Gramaj/hacim yoksa adet ('10 lu') okur. Bot ile ayni mantik."""
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


def anahtar_kelimeler(ad, n=4):
    dur = {"ve", "ile", "gr", "kg", "ml", "adet", "paket", "for"}
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
    cikti = []
    for u in d.get("data", {}).get("storeProductInfos", [])[:6]:
        sku = u.get("sku") or u.get("id")
        fiyat = u.get("regularPrice") or 0
        if not sku or not fiyat:
            continue
        cikti.append({"kod": str(sku), "ad": u.get("name", ""),
                      "fiyat": round(fiyat / 100, 2)})
    return cikti


def ozdilek_ara(sorgu):
    d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
              "/products/search?query=" + urllib.parse.quote(sorgu)
              + "&pageSize=6&currentPage=0&lang=tr&curr=TRY",
              {"Referer": "https://www.ozdilekteyim.com/",
               "Origin": "https://www.ozdilekteyim.com"})
    if not d:
        return []
    cikti = []
    for u in d.get("products", [])[:6]:
        kod = u.get("code")
        liste = (u.get("listPrice") or {}).get("value")
        fiyat = (u.get("price") or {}).get("value")
        deger = liste or fiyat
        if not kod or not deger:
            continue
        cikti.append({"kod": str(kod), "ad": u.get("name", ""),
                      "fiyat": round(float(deger), 2)})
    return cikti


def macro_ara(sorgu):
    d = getir("https://www.macrocenter.com.tr/rest/products/search?q="
              + urllib.parse.quote(sorgu))
    if not d:
        return []
    cikti = []
    for u in d.get("data", {}).get("storeProductInfos", [])[:6]:
        sku = u.get("sku") or u.get("id")
        fiyat = u.get("regularPrice") or 0
        if not sku or not fiyat:
            continue
        cikti.append({"kod": str(sku), "ad": u.get("name", ""),
                      "fiyat": round(fiyat / 100, 2)})
    return cikti


MARKETLER = [("migros", "MIGROS", migros_ara),
             ("ozdilek", "OZDILEK", ozdilek_ara),
             ("macro", "MACROCENTER", macro_ara)]


# ---------------------------------------------------------------- tablo

def tablo_yukle():
    """Eski bicimi (sku ust duzeyde = Migros) yeni bicime cevirir."""
    dosyalar = sorted(glob.glob("eslesmeler*.json"))
    if not dosyalar:
        print("eslesmeler.json bulunamadi — sifirdan baslaniyor.\n")
        return {}
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
        # eski bicim: sku/ad/carpan ust duzeyde -> migros
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
        print(f"  {cevrilen} eski Migros eslesmesi yeni bicime cevrildi")
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
        print("Dosya indiriliyor. Sonra 'ucuzcum-bot' deposuna yukle.")
    except Exception:
        print("Colab disi ortam: dosyayi elle al.")


# ---------------------------------------------------------------- ana dongu

def calis():
    tablo = tablo_yukle()

    urunler = getir(FB + "/urunler.json") or {}
    hedefler = []
    for k, v in urunler.items():
        if not isinstance(v, dict):
            continue
        ad = v.get("urun_adi", "")
        kayit = tablo.get(k, {})
        if kayit.get("atla"):
            continue
        # tum hedef marketler dolu mu?
        eksik = [m for m, _, _ in MARKETLER
                 if m not in kayit and v.get("market", "").lower() != m]
        if not eksik or not anahtar_kelimeler(ad):
            continue
        hedefler.append((k, v))

    # benzer urunler yan yana gelsin (grup atlama hizlansin)
    hedefler.sort(key=lambda x: normalize(x[1].get("urun_adi", "")))

    print(f"\nEslenecek urun: {len(hedefler)}")
    print("Tuslar: '1 2 0' sec | Enter gec | a atla | g grup atla | b bitir\n")

    atlanan_gruplar = set()
    i = 0
    while i < len(hedefler):
        urun_id, v = hedefler[i]
        ad = v.get("urun_adi", "")
        kel = anahtar_kelimeler(ad)
        i += 1

        # grup atlamasi devrede mi?
        if kel and kel[0] in atlanan_gruplar:
            tablo[urun_id] = {"atla": True}
            continue

        kayit = tablo.get(urun_id, {})
        hedef_miktar = miktar(ad)
        print("=" * 66)
        print(f"[{i}/{len(hedefler)}]  {ad}")
        print(f"   {v.get('market','')}  {v.get('gecerli_fiyat','')} TL"
              + (f"   (miktar: {hedef_miktar[0]} {hedef_miktar[1]})"
                 if hedef_miktar else "   (miktar okunamadi)"))

        sorgu = " ".join(kel)
        adaylar = {}
        for kod, baslik, ara in MARKETLER:
            if v.get("market", "").lower() == kod:
                print(f"\n{baslik}: (urunun kendi marketi)")
                adaylar[kod] = []
                continue
            if kod in kayit:
                print(f"\n{baslik}: ✓ zaten esli — {kayit[kod].get('ad','')[:44]}")
                adaylar[kod] = []
                continue
            sonuc = ara(sorgu)
            adaylar[kod] = sonuc
            print(f"\n{baslik}:")
            if not sonuc:
                print("   (sonuc yok)")
            for n, s in enumerate(sonuc, 1):
                m = miktar(s["ad"])
                isaret = "  <<" if (m and m == hedef_miktar) else ""
                print(f"   {n}) {s['ad'][:52]:54} {s['fiyat']} TL{isaret}")
            time.sleep(0.25)

        try:
            girdi = input("\nSecim: ").strip().lower()
        except EOFError:
            break

        if girdi == "b":
            break
        if girdi == "a":
            tablo[urun_id] = {"atla": True}
            print("  -> kalici atlandi")
            continue
        if girdi == "g":
            if kel:
                atlanan_gruplar.add(kel[0])
                tablo[urun_id] = {"atla": True}
                print(f"  -> '{kel[0]}' iceren tum urunler atlanacak")
            continue
        if not girdi:
            continue

        parcalar = girdi.split()
        yeni_kayit = dict(kayit)
        for sira, (kod, baslik, _) in enumerate(MARKETLER):
            if sira >= len(parcalar):
                break
            try:
                secim = int(parcalar[sira])
            except ValueError:
                continue
            if secim <= 0 or secim > len(adaylar.get(kod, [])):
                continue
            s = adaylar[kod][secim - 1]
            yeni_kayit[kod] = {"kod": s["kod"], "ad": s["ad"]}
            print(f"  {baslik} <- {s['ad'][:44]}")
        if yeni_kayit:
            tablo[urun_id] = yeni_kayit

    tablo_kaydet(tablo)


calis()
