"""
Ozdilek'in DEGERINI olc:
1) Indirimli urunleri toplu cekebiliyor muyuz? (hasDiscount filtresi)
2) Bu urunler Firebase'deki (diger market) urunlerle ortusuyor mu?
"""
import json, urllib.request, urllib.parse, re

B = {"User-Agent":"Mozilla/5.0 Chrome/126","Accept":"application/json",
     "Referer":"https://www.ozdilekteyim.com/","Origin":"https://www.ozdilekteyim.com"}
TEMEL = "https://api.ozdilekteyim.com/rest/v2/market-gecit-store"

def g(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=B),timeout=20) as c:
            return json.loads(c.read().decode("utf-8"))
    except Exception as e:
        print("hata:",type(e).__name__,str(e)[:60]); return None

def norm(s):
    s=s.lower()
    for a,b in zip("ışğüöçâî","isguocai"): s=s.replace(a,b)
    return re.sub(r"[^a-z0-9 ]"," ",s)

# 1) Indirimli urunleri sayfalayarak topla
print("1) OZDILEK INDIRIMLI URUNLER")
indirimli=[]
for sayfa in range(0,6):
    url=f"{TEMEL}/products/search?query=:relevance&pageSize=100&currentPage={sayfa}&lang=tr&curr=TRY"
    d=g(url)
    if not d or not d.get("products"): break
    for u in d["products"]:
        if u.get("price",{}).get("value") and u.get("listPrice",{}).get("value"):
            p=u["price"]["value"]; l=u["listPrice"]["value"]
            if p<l:
                indirimli.append({"ad":u.get("name",""),"fiyat":p,"liste":l,
                                  "oran":round((1-p/l)*100)})
    top=d.get("pagination",{}).get("totalResults",0)
print(f"  toplam katalog: {top} urun")
print(f"  ilk 600'de indirimli: {len(indirimli)}")
for x in indirimli[:8]:
    print(f"    {x['ad'][:45]:47} {x['fiyat']} <- {x['liste']} (%{x['oran']})")

# 2) Firebase urunleriyle ortusme
print("\n2) FIREBASE URUNLERIYLE ORTUSME")
fb=json.loads(urllib.request.urlopen("https://ucuzum-4e82f-default-rtdb.firebaseio.com/urunler.json",timeout=25).read())
fb_adlar=[norm(v.get("urun_adi","")) for v in fb.values() if isinstance(v,dict)]
def eslesme_ara(oz_ad):
    ok=set(norm(oz_ad).split())
    ok={w for w in ok if len(w)>2}
    if not ok: return False
    for fa in fb_adlar:
        fk=set(fa.split())
        if len(ok & fk)>=2: return True
    return False
# Ozdilek katalogundan orneklem al, kacinda eslesme var
ornek=g(f"{TEMEL}/products/search?query=:relevance&pageSize=60&currentPage=0&lang=tr&curr=TRY")
sayac=0; toplam=0
if ornek and ornek.get("products"):
    for u in ornek["products"]:
        ad=u.get("name","")
        if not ad: continue
        toplam+=1
        if eslesme_ara(ad): sayac+=1
print(f"  ornek {toplam} Ozdilek urunun {sayac} tanesi Firebase'de benzer ada sahip")
print(f"  ortusme orani: %{round(100*sayac/toplam) if toplam else 0}")
