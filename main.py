import os
import bcrypt
import uvicorn
from typing import Optional
from fastapi import FastAPI, Form, Request, Depends, Cookie
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
    
    nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == servis.id, ServisniNalog.status != "zavrseno").all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"servis": servis, "nalozi": nalozi})

@app.post("/dodaj-nalog")
def dodaj_nalog(
    ime_klijenta: str = Form(...),
    uredaj: str = Form(...),
    opis_kvara: str = Form(...),
    servis_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not servis_id: return RedirectResponse(url="/login")
    novi_nalog = ServisniNalog(servis_id=int(servis_id), ime_klijenta=ime_klijenta, uredaj=uredaj, opis_kvara=opis_kvara, status="zaprimljeno")
    db.add(novi_nalog)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/logout")
def odjava():
    odgovor = RedirectResponse(url="/login")
    odgovor.delete_cookie(key="servis_id")
    return odgovor

# --- POKRETANJE ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)