import os
import secrets
from typing import List
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal, Servis, ServisniNalog, Klijent

app = FastAPI(title="MobiFix SaaS - Otvorena Verzija za Faks")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Kreiranje tablica u lokalnoj bazi prilikom pokretanja
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally: 
        db.close()

# --- AUTOMATSKO KREIRANJE JEDNOG SERVISA ZA PROJEKT ---
# Čim se aplikacija pokrene, kreira se zadani servis (ID: 1) kako baza ne bi bila prazna
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        postojeci_servis = db.query(Servis).filter(Servis.id == 1).first()
        if not postojeci_servis:
            novi_servis = Servis(
                id=1,
                naziv_obrta="MobiFix Glavni Servis (Faks)",
                vlasnik_ime="Ante Orlović",
                email="test@servis.hr",
                lozinka_hash="otvoreno_bez_lozinke"
            )
            db.add(novi_servis)
            db.commit()
    finally:
        db.close()

# Fiksni ID servisa koji koristimo kroz cijelu aplikaciju budući da nema prijave
ZADANI_SERVIS_ID = 1

# =========================================================================
# 1. POČETNA STRANICA (Portal sa 3 kartice)
# =========================================================================
@app.get("/", response_class=HTMLResponse)
def pocetna_stranica(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# =========================================================================
# 2. PORTAL ZA KLIJENTE (Prijava popravke)
# =========================================================================
@app.get("/prijava-popravka", response_class=HTMLResponse)
def prikazi_obrazac(request: Request):
    return templates.TemplateResponse(request=request, name="prijava_popravka.html")

@app.post("/prijava-popravka")
def zaprimi_popravak(
    ime_prezime: str = Form(...),
    broj_telefona: str = Form(...),
    email: str = Form(...),
    brand: str = Form(...),
    model_uredaja: str = Form(...),
    opis_kvara: str = Form(...),
    oprema: List[str] = Form(default=[]),
    db: Session = Depends(get_db)
):
    # 1. Kreiranje klijenta (uvijek ga vežemo za zadani servis ID 1)
    klijent = Klijent(
        servis_id=ZADANI_SERVIS_ID, 
        ime_prezime=ime_prezime, 
        broj_telefona=broj_telefona, 
        email=email
    )
    db.add(klijent)
    db.flush() 
    
    # Spajanje opreme u opis kvara
    prosireni_opis = opis_kvara
    if oprema:
        prosireni_opis += f" | Donesena oprema: {', '.join(oprema)}"

    # 2. Kreiranje servisnog naloga
    nalog = ServisniNalog(
        servis_id=ZADANI_SERVIS_ID, 
        klijent_id=klijent.id, 
        tracking_token=secrets.token_hex(3).upper(),
        brand=brand, 
        model_uredjaja=model_uredaja, 
        opis_kvara=prosireni_opis,
        status='zaprimljeno'
    )
    
    db.add(nalog)
    db.commit()
    
    # Nakon prijave, idemo ravno u Admin panel da odmah vidiš nalog unutra!
    return RedirectResponse(url="/admin", status_code=303)

# =========================================================================
# 3. LAŽNE RUTE ZA LOGIN I REGISTER (Zadržavamo ih samo da HTML linkovi ne puknu)
# =========================================================================
@app.get("/register", response_class=HTMLResponse)
def prikazi_registraciju(request: Request):
    return RedirectResponse(url="/admin", status_code=303) # Odmah baci na admin

@app.get("/login", response_class=HTMLResponse)
def prikazi_login(request: Request):
    return RedirectResponse(url="/admin", status_code=303) # Odmah baci na admin

@app.get("/logout")
def izvrsi_logout():
    return RedirectResponse(url="/", status_code=303)

# =========================================================================
# 4. ADMIN PANEL (Potpuno otvoren za pregled)
# =========================================================================
@app.get("/admin", response_class=HTMLResponse)
def prikazi_admin_panel(request: Request, db: Session = Depends(get_db)):
    # Više ne provjeravamo cookie, samo dohvaćamo sve naloge za fiksni servis 1
    nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == ZADANI_SERVIS_ID).all()
    
    for nalog in nalozi:
        klijent = db.query(Klijent).filter(Klijent.id == nalog.klijent_id).first()
        nalog.ime_klijenta = klijent.ime_prezime if klijent else "Nepoznat Klijent"

    return templates.TemplateResponse(request=request, name="admin.html", context={"nalozi": nalozi})

@app.post("/admin/azuriraj-nalog/{nalog_id}")
def azuriraj_status_naloga(nalog_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == nalog_id, ServisniNalog.servis_id == ZADANI_SERVIS_ID).first()
    if nalog:
        nalog.status = status
        db.commit()
        
    return RedirectResponse(url="/admin", status_code=303)

# =========================================================================
# 5. SUPER ADMIN PANEL (Pregled i brisanje servisa)
# =========================================================================
@app.get("/super-admin", response_class=HTMLResponse)
def prikazi_super_admin(request: Request, db: Session = Depends(get_db)):
    servisi = db.query(Servis).all()
    izvjestaj = []
    
    for s in servisi:
        broj_naloga = db.query(ServisniNalog).filter(ServisniNalog.servis_id == s.id).count()
        izvjestaj.append({
            "podaci": s,
            "broj_naloga": broj_naloga
        })
        
    return templates.TemplateResponse(request=request, name="super_admin.html", context={"servisi": izvjestaj})

@app.post("/super-admin/obrisi-servis/{id_servisa}")
def obrisi_servis(id_servisa: int, db: Session = Depends(get_db)):
    db.query(ServisniNalog).filter(ServisniNalog.servis_id == id_servisa).delete()
    db.query(Klijent).filter(Klijent.servis_id == id_servisa).delete()
    db.query(Servis).filter(Servis.id == id_servisa).delete()
    db.commit()
    return RedirectResponse(url="/super-admin", status_code=303)