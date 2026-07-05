import os
import secrets
from typing import List, Optional
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal, Servis, ServisniNalog, Klijent

app = FastAPI(title="MobiFix SaaS - Otvorena Verzija za Faks")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Kreiranje tablica u bazi prilikom pokretanja
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally: 
        db.close()

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

ZADANI_SERVIS_ID = 1

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
    model_uredjaja: str = Form(...),
    imei_sn: Optional[str] = Form(""),
    opis_kvara: str = Form(...),
    oprema: List[str] = Form(default=[]),
    ostecen_ekran: int = Form(0),
    ostecenje_vlagom: int = Form(0),
    db: Session = Depends(get_db)
):
    klijent = Klijent(
        servis_id=ZADANI_SERVIS_ID, 
        ime_prezime=ime_prezime, 
        broj_telefona=broj_telefona, 
        email=email
    )
    db.add(klijent)
    db.flush() 
    
    prosireni_opis = opis_kvara
    if oprema:
        prosireni_opis += f" | Donesena oprema: {', '.join(oprema)}"

    nalog = ServisniNalog(
        servis_id=ZADANI_SERVIS_ID, 
        klijent_id=klijent.id, 
        tracking_token=secrets.token_hex(3).upper(),
        brand=brand, 
        model_uredjaja=model_uredjaja, 
        imei_sn=imei_sn,
        opis_kvara=prosireni_opis,
        status='zaprimljeno',
        napomena_servisera="",
        ostecen_ekran=ostecen_ekran,
        ostecenje_vlagom=ostecenje_vlagom
    )
    
    db.add(nalog)
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
def prikazi_admin_panel(request: Request, db: Session = Depends(get_db)):
    nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == ZADANI_SERVIS_ID).all()
    # Logika za spajanje klijenata ostaje ista
    for nalog in nalozi:
        klijent = db.query(Klijent).filter(Klijent.id == nalog.klijent_id).first()
        nalog.ime_klijenta = klijent.ime_prezime if klijent else "Nepoznat Klijent"
    return templates.TemplateResponse(request=request, name="admin.html", context={"nalozi": nalozi})

@app.post("/admin/uredi-nalog/{nalog_id}")
def uredi_nalog(
    nalog_id: int,
    ime_prezime: str = Form(...),
    brand: str = Form(...),
    model_uredjaja: str = Form(...),
    opis_kvara: str = Form(...),
    status: str = Form(...),
    ostecen_ekran: int = Form(0),
    ostecenje_vlagom: int = Form(0),
    db: Session = Depends(get_db)
):
    nalog = db.query(ServisniNalog).filter(ServisniNalog.id == nalog_id, ServisniNalog.servis_id == ZADANI_SERVIS_ID).first()
    if nalog:
        nalog.brand = brand
        nalog.model_uredjaja = model_uredjaja
        nalog.opis_kvara = opis_kvara
        nalog.status = status
        nalog.ostecen_ekran = ostecen_ekran
        nalog.ostecenje_vlagom = ostecenje_vlagom
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)