"""
UCUZCUM — ELLE URUN ESLESTIRME ARACI

Ne yapar:
  Firebase'deki Migros disi urunleri tek tek onune getirir,
  her biri icin Migros'tan en olasi 5 adayi fiyatiyla listeler.
  Sen sadece numara tuslarsin. Sonunda 'eslesmeler.json' dosyasi olusur.

Neden degerli:
  Urun kimlikleri kalicidir. Bir kez esletirdigin urun,
  gelecek kampanyalarda da otomatik eslesir. Tek seferlik emek.

KULLANIM (Colab):
  1) Bu dosyayi GitHub'daki 'ucuzcum-web' deposuna yukle
  2) Colab'da yeni bir hucreye:
       !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/eslestir.py -o e.py
  3) Baska bir hucreye:
       exec(open('e.py').read())

TUSLAR:
  1-5  -> o adayi esletir
  0    -> hicbiri uymuyor, gec
  y    -> kendi arama kelimeni yaz
  b    -> bitir ve kaydet
"""

import json
import re
import time
import urllib.parse
import urllib.request

FIREBASE = "https://ucuzum-4e82f-default-rtdb.firebaseio.com"
BASLIK = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
}
CIKTI = "eslesmeler.json"


# ---------------- yardimcilar ----------------

def istek(adres, deneme=2, sure=12):
    """Kisa zaman asimi + yeniden deneme (takilmayi onler)."""
    son_hata = None
    for _ in range(deneme):
        try:
            r = urllib.request.Request(adres, headers=BASLIK)
            with urllib.request.urlopen(r, timeout=sure) as c:
                return json.loads(c.read().decode("utf-8"))
        except Exception as e:
            son_hata = e
            time.sleep(1)
    raise son_hata


def tr(metin):
    metin = metin.lower()
    for a, b in {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
                 "é": "e", "è": "e", "â": "a", "î": "i", "û": "u"}.items():
        metin = metin.replace(a, b)
    return re.sub(r"[^a-z0-9 ]", " ", metin)


def miktar_metni(metin):
    """Miktar okuma icin: virgul, nokta ve carpim isaretini KORUR."""
    metin = metin.lower()
    for a, b in {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o",
                 "ç": "c"}.items():
        metin = metin.replace(a, b)
    return re.sub(r"[^a-z0-9,.x* ]", " ", metin)


def anahtar_kelimeler(ad, adet=4):
    return [w for w in tr(ad).split() if len(w) >= 3 and not w.isdigit()][:adet]


def toplam_miktar(ad):
    """
    Urun adindan TOPLAM miktari cikarir. Coklu paketleri carpar.
    '3x180 G' -> 540 g   |   '24x12,5 G' -> 300 g   |   '180 G' -> 180 g
    """
    metin = miktar_metni(ad)
    # once NxM kaliplari (3x180 g, 24 x 12,5 g)
    coklu = re.search(
        r"(\d+)\s*[x*]\s*(\d+[.,]?\d*)\s*(kg|gr|g|ml|lt|l|cl)\b", metin)
    if coklu:
        adet = int(coklu.group(1))
        birim_deger = float(coklu.group(2).replace(",", "."))
        birim = coklu.group(3)
        return _cevir(adet * birim_deger, birim)
    tek = re.findall(r"(\d+[.,]?\d*)\s*(kg|gr|g|ml|lt|l|cl)\b", metin)
    if tek:
        deger, birim = tek[-1]
        return _cevir(float(deger.replace(",", ".")), birim)
    return None


def _cevir(deger, birim):
    if birim == "kg":
        deger, birim = deger * 1000, "g"
    elif birim == "gr":
        birim = "g"
    elif birim in ("lt", "l"):
        deger, birim = deger * 1000, "ml"
    elif birim == "cl":
        deger, birim = deger * 10, "ml"
    return (round(deger, 2), birim)


def carpan_hesapla(kaynak_ad, migros_ad):
    """Iki urunun miktar orani. Ayni birimde degilse veya okunamazsa None."""
    a = toplam_miktar(kaynak_ad)
    b = toplam_miktar(migros_ad)
    if not a or not b or a[1] != b[1] or b[0] <= 0:
        return None
    oran = a[0] / b[0]
    # tam sayiya cok yakinsa yuvarla (3.0001 -> 3)
    if abs(oran - round(oran)) < 0.02:
        oran = float(round(oran))
    return round(oran, 3), a, b


def migros_ara(sorgu):
    adres = ("https://www.migros.com.tr/rest/products/search?q="
             + urllib.parse.quote(sorgu))
    try:
        veri = istek(adres)
        return veri.get("data", {}).get("storeProductInfos", [])[:5]
    except Exception as e:
        print(f"   [arama hatasi: {type(e).__name__} — 'y' ile tekrar dene]")
        return []


def tl(kurus):
    try:
        return round(float(kurus) / 100, 2)
    except Exception:
        return 0.0


def tablo_yukle():
    try:
        with open(CIKTI, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def tablo_kaydet(tablo):
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(tablo, f, ensure_ascii=False, indent=1)


# ---------------- ana akis ----------------

def calis():
    print("Firebase'den urunler cekiliyor...\n")
    urunler = istek(f"{FIREBASE}/urunler.json") or {}

    adaylar = []
    for urun_id, veri in urunler.items():
        if not isinstance(veri, dict):
            continue
        if veri.get("market") == "Migros":
            continue
        adaylar.append((urun_id, veri))

    # marketlere gore duzenli sira
    adaylar.sort(key=lambda x: (x[1].get("market", ""), x[1].get("urun_adi", "")))

    tablo = tablo_yukle()
    if tablo:
        eslesen = len([v for v in tablo.values()
                       if isinstance(v, dict) and v.get("sku")])
        atlanan = len(tablo) - eslesen
        print(f"Onceki oturum: {eslesen} eslesme, {atlanan} atlanan "
              f"(ikisi de tekrar sorulmaz)\n")

    kalan = [(i, v) for i, v in adaylar if i not in tablo]
    print(f"Toplam Migros disi urun : {len(adaylar)}")
    print(f"Eslestirilecek kalan    : {len(kalan)}")
    print("\nTuslar:  1-5 sec  |  0 gec  |  y kendi aramam  |  b bitir\n")
    print("=" * 64)

    yeni = 0
    for sira, (urun_id, veri) in enumerate(kalan, 1):
        ad = veri.get("urun_adi", "")
        market = veri.get("market", "?")
        fiyat = veri.get("gecerli_fiyat", 0)

        sorgu = " ".join(anahtar_kelimeler(ad))
        while True:
            print(f"\n[{sira}/{len(kalan)}]  {market}")
            print(f"   {ad}")
            print(f"   indirimli fiyat: {fiyat} TL")
            print(f"   (arama: {sorgu})")

            sonuclar = migros_ara(sorgu)
            if not sonuclar:
                print("   -> Migros'ta sonuc yok")
            for n, s in enumerate(sonuclar, 1):
                normal = tl(s.get("regularPrice") or 0)
                guncel = tl(s.get("shownPrice") or 0)
                notu = f"  (indirimli: {guncel})" if guncel and guncel != normal else ""
                print(f"   {n}) {s.get('name','')[:56]}")
                print(f"      normal: {normal} TL{notu}")

            secim = input("   secim > ").strip().lower()

            if secim == "b":
                tablo_kaydet(tablo)
                eslesen = len([v for v in tablo.values()
                               if isinstance(v, dict) and v.get("sku")])
                print(f"\nBitirildi. {eslesen} eslesme, "
                      f"{len(tablo) - eslesen} atlanan kaydedildi.")
                indir()
                return

            if secim == "y":
                sorgu = input("   yeni arama kelimesi > ").strip()
                if not sorgu:
                    sorgu = " ".join(anahtar_kelimeler(ad))
                continue

            if secim == "0" or secim == "":
                tablo[urun_id] = {"atla": True, "kaynak_ad": ad}
                tablo_kaydet(tablo)
                print("   – atlandi (bir daha sorulmayacak)")
                break

            if secim.isdigit() and 1 <= int(secim) <= len(sonuclar):
                s = sonuclar[int(secim) - 1]
                sku = s.get("sku") or s.get("id")
                migros_ad = s.get("name", "")
                migros_normal = tl(s.get("regularPrice") or 0)

                # --- miktar farki varsa carpan ---
                carpan = 1.0
                hesap = carpan_hesapla(ad, migros_ad)
                if hesap:
                    oran, a, b = hesap
                    if abs(oran - 1.0) > 0.02:
                        esdeger = round(migros_normal * oran, 2)
                        print(f"\n   ! MIKTAR FARKI")
                        print(f"     bu urun    : {a[0]:g} {a[1]}")
                        print(f"     migros     : {b[0]:g} {b[1]}  ({migros_normal} TL)")
                        print(f"     carpan     : {oran:g}  ->  "
                              f"migros esdeger: {esdeger} TL")
                        onay = input("     carpan dogru mu? [Enter=evet, "
                                     "sayi=elle gir, 0=eslestirme] > ").strip()
                        if onay == "0":
                            print("   - eslesme iptal")
                            break
                        if onay:
                            try:
                                oran = float(onay.replace(",", "."))
                            except ValueError:
                                pass
                        carpan = oran
                else:
                    elle = input("   miktar okunamadi. carpan "
                                 "[Enter=1] > ").strip()
                    if elle:
                        try:
                            carpan = float(elle.replace(",", "."))
                        except ValueError:
                            carpan = 1.0

                tablo[urun_id] = {
                    "sku": str(sku),
                    "ad": migros_ad,
                    "kaynak_ad": ad,
                    "carpan": carpan,
                }
                yeni += 1
                tablo_kaydet(tablo)          # her secimde kaydet
                print(f"   ✓ eslestirildi -> {s.get('name','')[:50]}"
                      f"   [toplam {len(tablo)}]")
                if len(tablo) % 25 == 0:
                    print("   ——— 25'in katı: 'b' ile indirip yedeklemen önerilir ———")
                break

            print("   ? gecersiz secim")

        time.sleep(0.15)

    tablo_kaydet(tablo)
    eslesen = len([v for v in tablo.values()
                   if isinstance(v, dict) and v.get("sku")])
    print(f"\n{'='*64}\nTAMAMLANDI. {eslesen} eslesme, "
          f"{len(tablo) - eslesen} atlanan.")
    indir()


def indir():
    """Colab'da dosyayi bilgisayara indirir."""
    try:
        from google.colab import files
        files.download(CIKTI)
        print(f"\n{CIKTI} indiriliyor... Bu dosyayi 'ucuzcum-bot' deposuna yukle.")
    except Exception:
        print(f"\n{CIKTI} olusturuldu. Colab sol paneldeki klasorden indirebilirsin.")


calis()
