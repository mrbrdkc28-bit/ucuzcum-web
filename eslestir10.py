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
    # Cozulemeyen carpan kalibi ("3x1 180 G" gibi) -> miktar okunamadi say.
    # Yoksa coklu paketi tekli sanip yanlis "ayni miktar" isareti veriyor.
    if re.search(r"\b\d+\s*[x*]\s*\d+", metin):
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




# ---------------------------------------------------------- carrefour (yerel)
# Carrefour'da arama yapamiyoruz (robots.txt /search yasakli).
# Bunun yerine laptop betiginin urettigi carrefour.json dosyasindaki
# katalogda arama yapariz. Ag istegi yok.

CARREFOUR_KATALOG = {}     # {kod: {"a": ad, "f": fiyat, "l": link}}


def carrefour_yukle():
    """carrefour.json varsa katalogu bellege alir."""
    global CARREFOUR_KATALOG
    dosyalar = sorted(glob.glob("carrefour*.json"))
    if not dosyalar:
        print("carrefour.json yok — Carrefour sorulmayacak.")
        print("  (ucuzcum-bot deposundan indirip Colab'a yukleyebilirsin)\n")
        return
    try:
        paket = json.load(open(dosyalar[-1]))
    except Exception as e:
        print(f"carrefour.json okunamadi: {type(e).__name__}\n")
        return
    CARREFOUR_KATALOG = paket.get("katalog") or {}
    yas = int(time.time()) - int(paket.get("toplama_zamani") or 0)
    print(f"Carrefour katalogu: {len(CARREFOUR_KATALOG)} urun "
          f"({yas // 3600} saatlik)\n")


def carrefour_ara(sorgu):
    """Yerel katalogda kelime bazli arama. Ag istegi yok."""
    if not CARREFOUR_KATALOG:
        return []
    kelimeler = [w for w in normalize(sorgu).split() if len(w) >= 3]
    if not kelimeler:
        return []
    puanli = []
    for kod, v in CARREFOUR_KATALOG.items():
        ad = v.get("a", "")
        if not ad:
            continue
        parcalar = set(normalize(ad).split())
        ortak = sum(1 for w in kelimeler if w in parcalar)
        if ortak == 0:
            continue
        # ilk kelime (marka) tutuyorsa one al
        puan = ortak * 10 + (5 if kelimeler[0] in parcalar else 0)
        puanli.append((puan, kod, ad, v.get("f", 0)))
    puanli.sort(reverse=True)
    return [{"kod": kod, "ad": ad, "fiyat": fiyat}
            for _, kod, ad, fiyat in puanli[:6]]


MARKETLER = [("migros", "MIGROS", migros_ara),
             ("ozdilek", "OZDILEK", ozdilek_ara),
             ("macro", "MACROCENTER", macro_ara),
             ("carrefour", "CARREFOUR", carrefour_ara)]

# Firebase'deki market adi ile tablo anahtari ayni degil (macro/Macrocenter)
FB_ADI = {"migros": "migros", "ozdilek": "ozdilek",
          "macro": "macrocenter", "carrefour": "carrefour"}


def kendi_marketi(urun, anahtar):
    return (urun.get("market", "") or "").strip().lower() == FB_ADI[anahtar]


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
        for m in ("migros", "ozdilek", "macro", "carrefour"):
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
        return "yok"
    for n, s in enumerate(adaylar, 1):
        m = miktar(s["ad"])
        isaret = "   << ayni miktar" if (m and m == hedef_m) else ""
        print(f"   {n}) {s['ad'][:50]:52} {s['fiyat']} TL{isaret}")
    while True:
        c = input(f"{baslik} (1-{len(adaylar)} / 0 veya Enter=yok / "
                  f"s=sil): ").strip().lower()
        if c in ("b",):
            raise Bitti("bitir")
        if c in ("a", "g"):
            raise Bitti(c)
        if c == "s":
            return "sil"          # mevcut eslesmeyi kaldir
        if c in ("0", ""):
            return "yok"          # bu markette yok, bir daha sorulmaz
        if c.isdigit() and 1 <= int(c) <= len(adaylar):
            return adaylar[int(c) - 1]
        print("   ge\u00e7ersiz. numara ya da 0 yaz.")


def calis():
    tablo = tablo_yukle()
    if tablo is None:
        return

    carrefour_yukle()

    urunler = getir(FB + "/urunler.json") or {}

    # Onceki hatali oturumdan kalan "kendi kendine eslesme" kayitlarini at
    temizlenen = 0
    for uid, v in urunler.items():
        if not isinstance(v, dict) or uid not in tablo:
            continue
        kyt = tablo[uid]
        if not isinstance(kyt, dict):
            continue
        for anahtar in ("migros", "ozdilek", "macro", "carrefour"):
            if kendi_marketi(v, anahtar) and anahtar in kyt:
                kyt.pop(anahtar, None)
                temizlenen += 1
    if temizlenen:
        print(f"  {temizlenen} hatali kendi-kendine eslesme temizlendi")
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
                 if m not in kayit
                 and (m + "_yok") not in kayit
                 and not kendi_marketi(v, m)]
        if eksik:
            hedefler.append((k, v))
    # Siralama: once HIC DOKUNULMAMIS urunler, en sonda yarim birakilanlar.
    # Boylece yarida kesip devam edince bastan ayni urunler gelmez.
    def _dokunuldu(uid):
        kyt = tablo.get(uid)
        return 1 if isinstance(kyt, dict) and kyt else 0

    hedefler.sort(key=lambda x: (_dokunuldu(x[0]),
                                 normalize(x[1].get("urun_adi", ""))))

    yeni = sum(1 for uid, _ in hedefler if not _dokunuldu(uid))
    yarim = len(hedefler) - yeni
    print(f"\nEslenecek urun: {len(hedefler)}"
          f"   (hic bakilmamis: {yeni}, yarim kalmis: {yarim})")
    if yarim:
        print("Yarim kalanlar listenin SONUNDA.")
    print("Tuslar:  numara=sec   0/Enter=bu markette yok   s=eslesmeyi sil")
    print("         a=urunu atla   g=grubu atla   b=bitir")
    print("Her karar kaydedilir; ayni soru bir daha sorulmaz.\n")

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
                if kendi_marketi(v, kod):
                    continue                      # kendi marketi
                if kayit.get(kod + "_yok"):
                    continue          # daha once "yok" denmis
                if kod in kayit:
                    mevcut = kayit[kod]
                    m_miktar = miktar(mevcut.get("ad", ""))
                    carpanli = mevcut.get("carpan") not in (None, 1, 1.0)
                    if carpanli or m_miktar == hedef_m:
                        print(f"\n{baslik}: zaten esli - "
                              f"{mevcut.get('ad','')[:40]}")
                        continue
                    # gramaj tutmuyor -> supheli, yeniden sor
                    print(f"\n{baslik}: !! SUPHELI ESLESME")
                    print(f"   mevcut: {mevcut.get('ad','')[:46]}"
                          f"  ({miktar_yazi(m_miktar)})")
                    print(f"   urun  : {ad[:46]}  ({miktar_yazi(hedef_m)})")
                    print("   0 = mevcut kalsin, numara = degistir")
                    print("   (s = mevcut eslesmeyi tamamen sil)")
                    secilen = soru(baslik, ara(sorgu), hedef_m)
                    if secilen == "sil":
                        kayit.pop(kod, None)
                        kayit[kod + "_yok"] = True
                        print("   -> eslesme silindi, bir daha sorulmayacak")
                    elif secilen and secilen != "yok":
                        kayit[kod] = {"kod": secilen["kod"],
                                      "ad": secilen["ad"]}
                        print("   -> duzeltildi")
                    else:
                        print("   -> mevcut eslesme korundu")
                    time.sleep(0.2)
                    continue
                secilen = soru(baslik, ara(sorgu), hedef_m)
                if secilen in ("yok", "sil"):
                    kayit[kod + "_yok"] = True
                elif secilen:
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
            bulunan = [m for m in ("migros", "ozdilek", "macro", "carrefour")
                       if m in kayit]
            if bulunan:
                print(f"   kaydedildi: {', '.join(bulunan)}")

        # Colab kopabiliyor: her 15 uronde diske yaz (indirme yok)
        if sayac % 15 == 0:
            with open(CIKTI, "w", encoding="utf-8") as f:
                json.dump(tablo, f, ensure_ascii=False, indent=1)
            print("   [ara kayit yapildi]")

    tablo_kaydet(tablo)


calis()
