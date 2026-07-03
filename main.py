import os
import secrets
from typing import List
from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

# Importi iz tvojih modula
from database import Base, engine, SessionLocal, Servis, ServisniNalog, Klijent
from utils.pdf_generator import create_ticket_pdf

# --- INICIJALIZACIJA ---
app = FastAPI(title="MobiFix SaaS - Otvorena Verzija")

# Montiranje statičkih datoteka (za CSS/Tailwind)
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Kreiranje tablica
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Zadani ID za projekt
ZADANI_SERVIS_ID = 1

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        if not db.query(Servis).filter(Servis.id == ZADANI_SERVIS_ID).first():
            novi_servis = Servis(
                id=ZADANI_SERVIS_ID,
                naziv_obrta="MobiFix Glavni Servis",
                vlasnik_ime="Ante Orlović",
                email="test@servis.hr"
            )
            db.add(novi_servis)
            db.commit()
    finally:
        db.close()

# --- RUTE ---

@app.get("/", response_class=HTMLResponse)
def pocetna_stranica(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

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
    klijent = Klijent(servis_id=ZADANI_SERVIS_ID, ime_prezime=ime_prezime, broj_telefona=broj_telefona, email=email)
    db.add(klijent)
    db.flush() 
    
    prosireni_opis = f"{opis_kvara} | Oprema: {', '.join(oprema)}" if oprema else opis_kvara

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
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
def prikazi_admin_panel(request: Request, db: Session = Depends(get_db)):
    nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == ZADANI_SERVIS_ID).all()
    for nalog in nalozi:
        klijent = db.query(Klijent).filter(Klijent.id == nalog.klijent_id).first()
        nalog.ime_klijenta = klijent.ime_prezime if klijent else "Nepoznat"
    return templates.TemplateResponse(request=request, name="admin.html", context={"nalozi": nalozi})

@app.get("/tickets/{ticket_id}/pdf")
def get_ticket_pdf(ticket_id: int, db: Session = Depends(get_db)):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == ticket_id).first()
    if not nalog:
        raise HTTPException(status_code=404, detail="Nalog nije pronađen")
    
    klijent = db.query(Klijent).filter(Klijent.id == nalog.klijent_id).first()
    
    data = {
        "ticket_number": f"IN{nalog.id}",
        "customer_name": klijent.ime_prezime if klijent else "N/A",
        "device_model": nalog.model_uredjaja,
        "description": nalog.opis_kvara
    }
    
    pdf_buffer = create_ticket_pdf(data)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=nalog_{nalog.id}.pdf"}
    )

# --- OSTALE RUTE (UREĐIVANJE/BRISANJE) ---
@app.post("/admin/azuriraj-nalog/{nalog_id}")
def azuriraj_status(nalog_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == nalog_id).first()
    if nalog:
        nalog.status = status
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/obrisi-nalog/{nalog_id}")
def obrisi_nalog(nalog_id: int, db: Session = Depends(get_db)):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == nalog_id).first()
    if nalog:
        db.delete(nalog)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

from fastapi.responses import Response
from utils.pdf_generator import create_ticket_pdf

@app.get("/tickets/{ticket_id}/pdf")
def get_ticket_pdf(ticket_id: int, db: Session = Depends(get_db)):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == ticket_id).first()
    klijent = db.query(Klijent).filter(Klijent.id == nalog.klijent_id).first()
    
    if not nalog:
        raise HTTPException(status_code=404, detail="Nalog nije pronađen")
    
    # Generiraj PDF bajtove
    pdf_content = create_ticket_pdf(nalog, klijent)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=nalog_{nalog.id}.pdf"}
    )