"""Macrocenter arama ucu - dogru sorgu formatini bul (Colab'da)"""
import json, urllib.request, urllib.parse

UA="Mozilla/5.0 Chrome/126"
def g(url):
    try:
        r=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
        c=urllib.request.urlopen(r,timeout=15)
        return c.status, json.loads(c.read().decode("utf-8"))
    except Exception as e:
        return f"H:{type(e).__name__}", None

print("MACROCENTER arama format denemeleri (sorgu: sut)\n")
denemeler = [
    "https://www.macrocenter.com.tr/rest/products/search?q=sut",
    "https://www.macrocenter.com.tr/rest/products/search?q=sut&sayfa=1",
    "https://www.macrocenter.com.tr/rest/search/screens/search?q=sut",
    "https://www.macrocenter.com.tr/rest/products/search-suggestion?q=sut",
    "https://www.macrocenter.com.tr/rest/products/search?q=süt",
    "https://www.macrocenter.com.tr/rest/products/search/infinite-scroll?q=sut",
]
for u in denemeler:
    kod, d = g(u)
    if d and isinstance(d, dict):
        data = d.get("data", {})
        # urun listesini bul
        n = 0; ornek = ""
        for key in ("storeProductInfos","products","searchStoreProductInfos","productSearchItems"):
            v = data.get(key) if isinstance(data,dict) else None
            if isinstance(v, list) and v:
                n = len(v)
                ornek = v[0].get("name","")[:40] if isinstance(v[0],dict) else ""
                break
        print(f"  {kod} | urun:{n} | {ornek}")
        print(f"       data anahtarlari: {list(data.keys())[:8] if isinstance(data,dict) else '?'}")
    else:
        print(f"  {kod} | {u.split('?')[0].split('/rest/')[-1]}")

# calisan formatta bir urunun fiyat yapisini goster
print("\n--- ORNEK URUN YAPISI ---")
kod, d = g("https://www.macrocenter.com.tr/rest/products/search?q=cikolata")
if d:
    lst = d.get("data",{}).get("storeProductInfos",[])
    if lst:
        u = lst[0]
        print("ad:", u.get("name"))
        print("regularPrice:", u.get("regularPrice"))
        print("price:", u.get("price"))
        print("anahtarlar:", [k for k in u.keys() if 'ric' in k.lower() or 'name' in k.lower()])
