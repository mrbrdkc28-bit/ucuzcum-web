"""
Ozdilek karsilastirma degeri olcumu.
productIds ile calisiyor; once toplu urun listeleyen bir uc var mi ona bakariz,
yoksa carousel'den ornek fiyatlar cekip yapiyi anlariz.
"""
import json, urllib.request, urllib.error

B = {"User-Agent":"Mozilla/5.0 Chrome/126","Accept":"application/json",
     "Referer":"https://www.ozdilekteyim.com/","Origin":"https://www.ozdilekteyim.com"}

def g(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=B),timeout=18) as c:
            return c.status, json.loads(c.read().decode("utf-8"))
    except urllib.error.HTTPError as h:
        return h.code, None
    except Exception as e:
        return f"H:{type(e).__name__}", None

TEMEL = "https://api.ozdilekteyim.com/rest/v2/market-gecit-store"

# 1) Toplu urun/kategori listeleme ucu var mi?
print("1) TOPLU LISTELEME UCU ARAMASI")
for yol in [
    "/products/search?query=:relevance&pageSize=20&lang=tr&curr=TRY",
    "/products/search?query=sut&pageSize=10&lang=tr&curr=TRY",
    "/products?pageSize=20&lang=tr&curr=TRY",
    "/categories?lang=tr&curr=TRY",
    "/products/campaigns?lang=tr&curr=TRY",
]:
    kod, veri = g(TEMEL+yol)
    isaret=""
    if isinstance(veri,dict):
        isaret=f" -> anahtar: {list(veri.keys())[:6]}"
    print(f"  {kod}  {yol[:50]}{isaret}")

# 2) Carousel'den ornek fiyat yapisi
print("\n2) ORNEK URUN FIYATLARI (carousel)")
ids = "10001704,10003883,14300045,10120632,10001710,10003548,10003603"
kod, veri = g(f"{TEMEL}/products/carousel?productIds={ids}&fields=FULL&lang=tr&curr=TRY")
if isinstance(veri,dict) and veri.get("products"):
    for u in veri["products"][:8]:
        ad = u.get("name","?")
        fiyat = u.get("price",{}).get("value")
        liste = u.get("listPrice",{}).get("value")
        ind = u.get("hasDiscount")
        print(f"  {ad[:45]:47} {fiyat} TL"
              + (f" (liste {liste}, indirim:{ind})" if liste else ""))
else:
    print("  carousel alinamadi:", kod)

# 3) Arama ucu calisiyorsa kac urun donuyor
print("\n3) ARAMA UCU (kategori/toplu cekim mumkun mu)")
kod, veri = g(f"{TEMEL}/products/search?query=:relevance:&pageSize=5&currentPage=0&lang=tr&curr=TRY")
if isinstance(veri,dict):
    print("  anahtarlar:", list(veri.keys())[:8])
    if "pagination" in veri:
        print("  toplam urun:", veri["pagination"].get("totalResults"))
    if veri.get("products"):
        print("  ornek:", veri["products"][0].get("name","")[:40])
else:
    print("  durum:", kod)
