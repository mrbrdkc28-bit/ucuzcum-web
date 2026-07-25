"""
A101/BIM/Mopas/Macrocenter'da ARAMA UCU var mi?
Karsilastirma icin bir urunu o markette aratabilmemiz sart.
Colab'da calistir (bu sunucu 403 verebilir).
"""
import json, urllib.request, urllib.error, urllib.parse

UA="Mozilla/5.0 Chrome/126"
def dene(ad, url, post=None, baslik=None):
    h={"User-Agent":UA,"Accept":"application/json"}
    if baslik: h.update(baslik)
    try:
        if post is not None:
            r=urllib.request.Request(url,data=json.dumps(post).encode(),headers=h,method="POST")
        else:
            r=urllib.request.Request(url,headers=h)
        c=urllib.request.urlopen(r,timeout=15)
        raw=c.read().decode("utf-8","ignore")
        try:
            d=json.loads(raw)
            n=0
            for key in ("products","data","content","items","results"):
                v=d.get(key) if isinstance(d,dict) else None
                if isinstance(v,list): n=len(v); break
                if isinstance(v,dict):
                    for k2 in ("products","content","items"):
                        if isinstance(v.get(k2),list): n=len(v[k2]); break
            print(f"  {c.status} {ad}: JSON, ~{n} urun  anahtar={list(d.keys())[:5] if isinstance(d,dict) else 'liste'}")
        except:
            fiy=len([x for x in __import__('re').findall(r'\d+[.,]\d{2}',raw)])
            print(f"  {c.status} {ad}: JSON degil ({len(raw)}b, {fiy} sayi)")
    except urllib.error.HTTPError as e:
        print(f"  {e.code} {ad}: engel/yok")
    except Exception as e:
        print(f"  -- {ad}: {type(e).__name__}")

print("A101 arama denemeleri:")
dene("a101 search", "https://www.a101.com.tr/api/v1/search?q=sut")
dene("a101 kapida", "https://api.a101.com.tr/search?keyword=sut")
dene("a101 site", "https://www.a101.com.tr/arama?k=sut")

print("\nBIM arama denemeleri:")
dene("bim search", "https://www.bim.com.tr/Search?q=sut")
dene("bim api", "https://api.bim.com.tr/products/search?q=sut")

print("\nMopas arama denemeleri:")
dene("mopas search", "https://www.mopas.com.tr/arama?q=sut")
dene("mopas api", "https://www.mopas.com.tr/api/search?q=sut")

print("\nMacrocenter arama denemeleri:")
dene("macro search", "https://www.macrocenter.com.tr/rest/products/search?q=sut")
dene("macro api", "https://www.macrocenter.com.tr/api/products?search=sut")

print("\n(200 + urun donen bir uc varsa o market karsilastirmaya HEDEF olabilir)")
