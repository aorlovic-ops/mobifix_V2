import os
import bcrypt
import secrets
from typing import Optional
from fastapi import FastAPI, Form, Request, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, Servis, ServisniNalog, Klijent

app = FastAPI(title="MobiFix SaaS")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- RUTE ZA REGISTRACIJU I LOGIN ---
@app.post("/register")
def izvrši_registraciju(
    naziv_obrta: str = Form(...),
    vlasnik_ime: str = Form(...),
    email: str = Form(...),
    lozinka: str = Form(...),
    db: Session = Depends(get_db)
):
    # Koristi bcrypt za hashiranje
    hashed = bcrypt.hashpw(lozinka.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    novi_servis = Servis(naziv_obrta=naziv_obrta, vlasnik_ime=vlasnik_ime, email=email, lozinka_hash=hashed)
    db.add(novi_servis)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/dodaj-nalog")
def dodaj_nalog(
    ime_klijenta: str = Form(...),
    broj_telefona: str = Form(...),
    email: str = Form(...),
    brand: str = Form(...),
    model_uredjaja: str = Form(...),
    opis_kvara: str = Form(...),
    servis_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    # 1. Kreiraj klijenta
    klijent = Klijent(servis_id=int(servis_id), ime_prezime=ime_klijenta, broj_telefona=broj_telefona, email=email)
    db.add(klijent)
    db.flush() # Dobijemo ID klijenta
    
    # 2. Kreiraj nalog
    nalog = ServisniNalog(
        servis_id=int(servis_id), klijent_id=klijent.id, 
        tracking_token=secrets.token_hex(3).upper(),
        brand=brand, model_uredjaja=model_uredjaja, opis_kvara=opis_kvara
    )
    db.add(nalog)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# --- RUTA ZA DODAVANJE NALOGA (USKLAĐENA S BAZOM) ---
@app.post("/dodaj-nalog")
def dodaj_nalog(
    ime_klijenta: str = Form(...),
    broj_telefona: str = Form(...),
    email: str = Form(...),
    brand: str = Form(...),
    model_uredjaja: str = Form(...),
    opis_kvara: str = Form(...),
    servis_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not servis_id: return RedirectResponse(url="/login")
    
    # 1. Prvo kreiramo klijenta jer nalog zahtijeva klijent_id
    novi_klijent = Klijent(servis_id=int(servis_id), ime_prezime=ime_klijenta, broj_telefona=broj_telefona, email=email)
    db.add(novi_klijent)
    db.flush() # Dobivamo ID bez commit-a
    
    # 2. Sada kreiramo nalog sa svim obaveznim poljima iz baze
    novi_nalog = ServisniNalog(
        servis_id=int(servis_id),
        klijent_id=novi_klijent.id,
        tracking_token=secrets.token_hex(3).upper(),
        brand=brand,
        model_uredjaja=model_uredjaja,
        serijski_imei="N/A",
        opis_kvara=opis_kvara,
        status="zaprimljeno"
    )
    db.add(novi_nalog)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)