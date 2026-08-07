"""
UCUZCUM — ESLESME TEMIZLEYICI

Tablodaki TUM eslesmeleri tarar, gramaji tutmayanlari bulur ve:
  1) O markette dogru gramajli urun varsa OTOMATIK duzeltir
  2) Yoksa eslesmeyi kaldirir (yanlis fiyat gostermektense hic gosterme)

Carpanli kayitlara (coklu paket) dokunmaz.
Once RAPOR verir, onaydan sonra yazar.

KULLANIM (Colab):
  1) eslesmeler.json'i Colab'a yukle
  2) !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/temizle.py -o t.py
  3) exec(open('t.py').read())
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


def migros_ara(sorgu):
    d = getir("https://www.migros.com.tr/rest/products/search?q="
              + urllib.parse.quote(sorgu))
    out = []
    for u in (d or {}).get("data", {}).get("storeProductInfos", [])[:8]:
        sku = u.get("sku") or u.get("id")
        if sku:
            out.append({"kod": str(sku), "ad": u.get("name", "")})
    return out


def ozdilek_ara(sorgu):
    d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
              "/products/search?query=" + urllib.parse.quote(sorgu)
              + "&pageSize=8&currentPage=0&lang=tr&curr=TRY",
              {"Referer": "https://www.ozdilekteyim.com/",
               "Origin": "https://www.ozdilekteyim.com"})
    out = []
    for u in (d or {}).get("products", [])[:8]:
        if u.get("code"):
            out.append({"kod": str(u["code"]), "ad": u.get("name", "")})
    return out


def macro_ara(sorgu):
    d = getir("https://www.macrocenter.com.tr/rest/products/search?q="
              + urllib.parse.quote(sorgu))
    out = []
    for u in (d or {}).get("data", {}).get("storeProductInfos", [])[:8]:
        sku = u.get("sku") or u.get("id")
        if sku:
            out.append({"kod": str(sku), "ad": u.get("name", "")})
    return out


ARAMA = {"migros": migros_ara, "ozdilek": ozdilek_ara, "macro": macro_ara}


def calis():
    dosyalar = sorted(glob.glob("eslesmeler*.json"))
    if not dosyalar:
        print("eslesmeler.json bulunamadi. Once Colab'a yukle.")
        return
    tablo = json.load(open(dosyalar[-1]))
    print(f"Tablo: {dosyalar[-1]}  ({len(tablo)} kayit)")

    urunler = getir(FB + "/urunler.json") or {}
    print(f"Firebase: {len(urunler)} urun\n")

    supheli = []
    for uid, kayit in tablo.items():
        if not isinstance(kayit, dict) or kayit.get("atla"):
            continue
        urun = urunler.get(uid)
        if not isinstance(urun, dict):
            continue
        hedef = miktar(urun.get("urun_adi", ""))
        if not hedef:
            continue
        for market in ("migros", "ozdilek", "macro"):
            esl = kayit.get(market)
            if not isinstance(esl, dict):
                continue
            # Kullanici elle onayladiysa dokunma
            if esl.get("onay"):
                continue
            if esl.get("carpan") not in (None, 1, 1.0):
                continue                      # coklu paket, normal
            m = miktar(esl.get("ad", ""))
            if m != hedef:
                supheli.append((uid, market, urun.get("urun_adi", ""),
                                esl.get("ad", ""), hedef, m))

    print(f"GRAMAJI TUTMAYAN ESLESME: {len(supheli)}\n")
    for uid, market, u_ad, e_ad, h, m in supheli[:15]:
        print(f"  [{market}] {u_ad[:38]} ({h[0] if h else '?'} {h[1] if h else ''})")
        print(f"        -> {e_ad[:44]} ({m[0] if m else '?'} {m[1] if m else ''})")
    if len(supheli) > 15:
        print(f"  ... +{len(supheli)-15} tane daha")

    if not supheli:
        print("Temizlenecek bir sey yok.")
        return

    onay = input(f"\n{len(supheli)} kaydi duzelt/kaldir? (e/h): ").strip().lower()
    if onay != "e":
        print("Iptal edildi, dosya degismedi.")
        return

    duzeltilen = silinen = 0
    for i, (uid, market, u_ad, e_ad, hedef, _) in enumerate(supheli, 1):
        kel = anahtar_kelimeler(u_ad)
        dogru = None
        if kel:
            for aday in ARAMA[market](" ".join(kel)):
                if miktar(aday["ad"]) == hedef:
                    dogru = aday
                    break
        if dogru:
            tablo[uid][market] = {"kod": dogru["kod"], "ad": dogru["ad"]}
            duzeltilen += 1
            print(f"  {i}. duzeltildi: {dogru['ad'][:46]}")
        else:
            tablo[uid].pop(market, None)
            tablo[uid][market + "_yok"] = True
            silinen += 1
            print(f"  {i}. kaldirildi: {u_ad[:46]} [{market}]")
        time.sleep(0.25)

    with open("eslesmeler.json", "w", encoding="utf-8") as f:
        json.dump(tablo, f, ensure_ascii=False, indent=1)
    print(f"\nBitti — {duzeltilen} duzeltildi, {silinen} kaldirildi")
    try:
        from google.colab import files
        files.download("eslesmeler.json")
        print("Dosya indi. 'ucuzcum-bot' deposuna yukle.")
    except Exception:
        pass


calis()
