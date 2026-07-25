"""
ESLENMEYECEKLERI listele (Colab'da calistir):
Migros-disi urunlerden karsilastirmaya GIRMEYENLERI 3 gruba ayirir:
  1) Elle "atla" isaretlenenler (eslesmeler.json'da atla:true)
  2) Gramaji okunamayanlar (aranamaz - karpuz, et vb.)
  3) Tabloda hic olmayanlar (henuz eslenmemis)
"""
import json, re, glob, urllib.request

FB = "https://ucuzum-4e82f-default-rtdb.firebaseio.com"

def norm(s):
    s=s.lower()
    for a,b in zip("ışğüöçâî","isguocai"): s=s.replace(a,b)
    return re.sub(r"[^a-z0-9 ]"," ",s)

def miktar(ad):
    m=re.search(r"(\d+[.,]?\d*)\s*(kg|g|gr|ml|lt|l|cl|adet|li|lu)", ad.lower())
    return bool(m)

# eslesmeler.json bul
dosyalar=sorted(glob.glob("eslesmeler*.json"))
tablo={}
if dosyalar:
    tablo=json.load(open(dosyalar[-1]))
    print(f"Eslesme tablosu: {dosyalar[-1]} ({len(tablo)} kayit)\n")
else:
    print("UYARI: eslesmeler.json bulunamadi, elle 'atla' grubu bos gelecek\n")

urunler=json.loads(urllib.request.urlopen(FB+"/urunler.json",timeout=25).read())
hedef=[(k,v) for k,v in urunler.items() if isinstance(v,dict) and v.get("market")!="Migros"]

elle_atla=[]      # sen atla dedin
gramaj_yok=[]     # aranamiyor
tabloda_yok=[]    # henuz eslenmemis (gramaji var ama tabloda yok)
karsilastirmali=[] # zaten karsilastirmasi var

for k,v in hedef:
    ad=v.get("urun_adi","")
    kayit=tablo.get(k)
    if isinstance(kayit,dict) and kayit.get("atla"):
        elle_atla.append(ad)
    elif v.get("karsilastirma"):
        karsilastirmali.append(ad)
    elif not miktar(ad):
        gramaj_yok.append(ad)
    elif k not in tablo:
        tabloda_yok.append(ad)

print("="*58)
print(f"1) ELLE 'ATLA' ISARETLENENLER: {len(elle_atla)}")
print("   (sen bilerek disladin - karpuz, et vb.)")
for a in elle_atla[:20]: print(f"   - {a[:50]}")
if len(elle_atla)>20: print(f"   ... +{len(elle_atla)-20} tane daha")

print("\n"+"="*58)
print(f"2) GRAMAJI OKUNAMAYAN (aranamiyor): {len(gramaj_yok)}")
print("   (agirlikli/adetsiz - otomatik aranamaz)")
for a in gramaj_yok[:20]: print(f"   - {a[:50]}")
if len(gramaj_yok)>20: print(f"   ... +{len(gramaj_yok)-20} tane daha")

print("\n"+"="*58)
print(f"3) TABLODA YOK ama gramaji okunabilir: {len(tabloda_yok)}")
print("   (otomatik aranir; tutmazsa elle eklenebilir)")
for a in tabloda_yok[:20]: print(f"   - {a[:50]}")
if len(tabloda_yok)>20: print(f"   ... +{len(tabloda_yok)-20} tane daha")

print("\n"+"="*58)
print(f"OZET: {len(hedef)} Migros-disi urun")
print(f"  zaten karsilastirmali : {len(karsilastirmali)}")
print(f"  elle atlanmis         : {len(elle_atla)}")
print(f"  gramaj yok (aranamaz) : {len(gramaj_yok)}")
print(f"  tabloda yok           : {len(tabloda_yok)}")
