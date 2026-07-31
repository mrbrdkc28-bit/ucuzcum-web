"""
UCUZCUM — URUN LINKI TESHISI

Migros, Macrocenter ve Ozdilek'in urun adresini hangi alanda dondurdugunu
ve bizim urettigimiz linki yan yana gosterir.

KULLANIM (Colab):
  ucuzcum-web'e yukle, sonra:
  !curl -sL https://raw.githubusercontent.com/mrbrdkc28-bit/ucuzcum-web/main/link_teshis.py -o lt.py
  exec(open('lt.py').read())
"""

import json
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def getir(url, baslik=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if baslik:
        h.update(baslik)
    try:
        r = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(r, timeout=20) as c:
            return json.loads(c.read().decode("utf-8"))
    except Exception as e:
        print("  hata:", type(e).__name__, str(e)[:70])
        return None


def alanlari_yaz(dto, alanlar):
    for a in alanlar:
        deger = dto.get(a)
        if isinstance(deger, (dict, list)):
            deger = json.dumps(deger, ensure_ascii=False)[:70]
        print(f"    {a:16} = {str(deger)[:70]}")


print("=" * 64)
print("1) MIGROS")
d = getir("https://www.migros.com.tr/rest/products/search?q=nutella")
liste = (d or {}).get("data", {}).get("storeProductInfos", [])
if liste:
    u = liste[0]
    print("  ad:", u.get("name", "")[:56])
    alanlari_yaz(u, ["sku", "id", "prettyName", "seoUrl", "url", "slug"])
    guzel = (u.get("prettyName") or "").strip("/")
    sku = u.get("sku") or u.get("id")
    print(f"\n  BIZIM URETTIGIMIZ (karsilastirma):")
    print(f"    https://www.migros.com.tr/{guzel}-p-{sku}")
    print(f"  BIZIM URETTIGIMIZ (urun karti):")
    print(f"    https://www.migros.com.tr/{guzel}")
    print("\n  >> Tarayicida ikisini de dene, hangisi acilirsa onu kullanacagiz")
else:
    print("  urun alinamadi")

print("\n" + "=" * 64)
print("2) MACROCENTER")
d = getir("https://www.macrocenter.com.tr/rest/products/search?q=cikolata")
liste = (d or {}).get("data", {}).get("storeProductInfos", [])
if liste:
    u = liste[0]
    print("  ad:", u.get("name", "")[:56])
    alanlari_yaz(u, ["sku", "id", "prettyName", "seoUrl", "url", "slug"])
    guzel = (u.get("prettyName") or "").strip("/")
    sku = u.get("sku") or u.get("id")
    print(f"\n  BIZIM URETTIGIMIZ:")
    print(f"    https://www.macrocenter.com.tr/{guzel}-p-{sku}")
    print(f"    https://www.macrocenter.com.tr/{guzel}")
else:
    print("  urun alinamadi")

print("\n" + "=" * 64)
print("3) OZDILEK")
d = getir("https://api.ozdilekteyim.com/rest/v2/market-gecit-store"
          "/products/search?query=cikolata&pageSize=3&currentPage=0"
          "&lang=tr&curr=TRY",
          {"Referer": "https://www.ozdilekteyim.com/",
           "Origin": "https://www.ozdilekteyim.com"})
liste = (d or {}).get("products", [])
if liste:
    u = liste[0]
    print("  ad:", u.get("name", "")[:56])
    alanlari_yaz(u, ["code", "url", "customUrl", "baseProduct", "slug"])
    yol = (u.get("url") or u.get("customUrl") or "").strip()
    print(f"\n  BIZIM URETTIGIMIZ:")
    if yol.startswith("/"):
        print(f"    https://www.ozdilekteyim.com{yol}")
    else:
        print(f"    {yol or '(bos)'}")
else:
    print("  urun alinamadi")

print("\n" + "=" * 64)
print("Ciktinin TAMAMINI kopyala. Ayrica tarayicidan bu uc siteden")
print("birer urun sayfasi acip adres cubugundaki linki de gonder.")
