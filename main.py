import os
import bcrypt
from typing import Optional
from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, Servis, ServisniNalog

# --- KONFIGURACIJA ---
app = FastAPI(title="MobiFix SaaS")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- DEPENDENCY ZA BAZU ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- RUTE ---

@app.get("/", response_class=HTMLResponse)
def read_root():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def prikaži_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

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
    
    # UPIT SE SADA NALAZI OVDJE, UNUTAR FUNKCIJE
    nalozi = db.query(ServisniNalog).filter(
        ServisniNalog.servis_id == servis.id,
        ServisniNalog.status != "zavrseno"
    ).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="admin.html", 
        context={"servis": servis, "nalozi": nalozi}
    )

@app.get("/logout")
def odjava():
    odgovor = RedirectResponse(url="/login")
    odgovor.delete_cookie(key="servis_id")
    return odgovor