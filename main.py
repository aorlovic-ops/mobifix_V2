import os
import uuid
import bcrypt
import smtplib
import secrets
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, Form, Request, HTTPException, Depends, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from database import SessionLocal, Servis, Klijent, ServisniNalog, User  # Pretpostavljam da si User dodao u models/database.py

# --- KONFIGURACIJA ---
app = FastAPI(title="MobiFix SaaS")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
security = HTTPBasic()

# --- DEPENDENCY ZA BAZU ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- POMOĆNE FUNKCIJE ---
def pošalji_email_obavijest(primatelj_email, ime_klijenta, token, novi_status, brand, model):
    # (Tvoja logika za email ostaje ista)
    pass

def provjeri_super_admin_ovlasti(credentials: HTTPBasicCredentials = Depends(security)):
    if not (secrets.compare_digest(credentials.username, "admin") and 
            secrets.compare_digest(credentials.password, "ZgMaster2026!")):
        raise HTTPException(status_code=401, detail="Neautorizirano", headers={"WWW-Authenticate": "Basic"})
    return credentials.username

# --- RUTE ---
@app.get("/")
def read_root():
    return {"message": "Sada radi!"}
@app.get("/", response_class=HTMLResponse)
def read_root():
    return RedirectResponse(url="/login")

@app.get("/register", response_class=HTMLResponse)
def prikaži_registraciju(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def izvrši_registraciju(
    naziv_obrta: str = Form(...),
    vlasnik_ime: str = Form(...),
    email: str = Form(...),
    lozinka: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(Servis).filter(Servis.email == email).first():
        return HTMLResponse("Email je već registriran!", status_code=400)
    
    hashed = bcrypt.hashpw(lozinka.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    novi_servis = Servis(naziv_obrta=naziv_obrta, vlasnik_ime=vlasnik_ime, email=email, lozinka_hash=hashed)
    
    db.add(novi_servis)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

@app.post("/login")
def izvrši_prijavu(email: str = Form(...), lozinka: str = Form(...), db: Session = Depends(get_db)):
    servis = db.query(Servis).filter(Servis.email == email).first()
    if not servis or not bcrypt.checkpw(lozinka.encode('utf-8'), servis.lozinka_hash.encode('utf-8')):
        return HTMLResponse("Krivi podaci!", status_code=400)
    
    odgovor = RedirectResponse(url="/admin", status_code=303)
    odgovor.set_cookie(key="servis_id", value=str(servis.id), httponly=True)
    return odgovor

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, servis_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not servis_id: return RedirectResponse(url="/login")
    servis = db.query(Servis).filter(Servis.id == int(servis_id)).first()
    if not servis: return RedirectResponse(url="/login")
    
    nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == servis.id).all()
    return templates.TemplateResponse("admin.html", {"request": request, "servis": servis, "nalozi": nalozi})

@app.get("/logout")
def odjava():
    odgovor = RedirectResponse(url="/login")
    odgovor.delete_cookie(key="servis_id")
    return odgovor