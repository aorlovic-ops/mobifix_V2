import os
import uuid
import bcrypt
import smtplib
from typing import List, Optional  
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, Form, Request, HTTPException, Depends, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, Servis, Klijent, ServisniNalog

print("--- KOD JE USPJEŠNO UČITAN I RADI! ---")

app = FastAPI(title="MobiFix SaaS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- KONFIGURACIJA ZA SLANJE EMAILOVA ---
SMTP_SERVER = "smtp.gmail.com"          
SMTP_PORT = 587                         
SENDER_EMAIL = "tvoj.servis@gmail.com"  
SENDER_PASSWORD = "tvoj_app_password"   

# Dependency za dohvaćanje baze podataka po svakom zahtjevu
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- POMOĆNA FUNKCIJA ZA EMAIL OBAVIJESTI ---
def pošalji_email_obavijest(primatelj_email: str, ime_klijenta: str, token: str, novi_status: str, brand: str, model: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = primatelj_email
        msg['Subject'] = f"MobiFix - Promjena statusa naloga #{token}"

        status_tekst = novi_status
        if novi_status == "zaprimljeno":
            status_tekst = "ZAPRIMLJENO (Vaš nalog čeka na red za dijagnostiku)"
        elif novi_status == "u_radu":
            status_tekst = "U RADU (Uređaj je na servisnom stolu i aktivno se popravlja)"
        elif novi_status == "zavrseno":
            status_tekst = "ZAVRŠENO (Uređaj je uspješno popravljen i spreman za preuzimanje!)"

        poruka = f"""Pozdrav {ime_klijenta},

Obavještavamo Vas da je status Vašeg servisnog naloga #{token} uspješno ažuriran.

Uređaj: {brand.upper()} {model}
Novi status: {status_tekst}

Hvala Vam na povjerenju!
Vaš MobiFix Servis
"""
        msg.attach(MIMEText(poruka, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, primatelj_email, msg.as_string())
        server.quit()
        print(f"--- Email uspješno poslan na {primatelj_email} ---")
    except Exception as e:
        print(f"--- Greška pri slanju emaila: {str(e)} ---")

# --- KORIJEN ---
@app.get("/", response_class=HTMLResponse)
def ruter_korijen(request: Request):
    return RedirectResponse(url="/login", status_code=302)

# --- REGISTRACIJA ---
@app.get("/register", response_class=HTMLResponse)
def prikaži_stranicu_registracije(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def izvrši_snimanje_registracije(
    naziv_obrta: str = Form(...),
    vlasnik_ime: str = Form(...),
    email: str = Form(...),
    lozinka: str = Form(...),
    db: Session = Depends(get_db)
):
    postojeci_servis = db.query(Servis).filter(Servis.email == email).first()
    if postojeci_servis:
        return HTMLResponse(content="<h3>Email je već registriran!</h3>", status_code=400)
    
    sol = bcrypt.gensalt()
    hashed = bcrypt.hashpw(lozinka.encode('utf-8'), sol).decode('utf-8')
    
    novi_servis = Servis(
        naziv_obrta=naziv_obrta,
        vlasnik_ime=vlasnik_ime,
        email=email,
        lozinka_hash=hashed
    )
    
    db.add(novi_servis)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=302)

# --- PRIJAVA (LOGIN) - Sada postavlja Cookie ---
@app.get("/login", response_class=HTMLResponse)
def prikaži_stranicu_prijave(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def izvrši_provjeru_prijave(
    email: str = Form(...),
    lozinka: str = Form(...),
    db: Session = Depends(get_db)
):
    servis = db.query(Servis).filter(Servis.email == email).first()
    if not servis:
        return HTMLResponse(content="<h3>Krivi email ili lozinka!</h3>", status_code=400)
    
    if not bcrypt.checkpw(lozinka.encode('utf-8'), servis.lozinka_hash.encode('utf-8')):
        return HTMLResponse(content="<h3>Krivi email ili lozinka!</h3>", status_code=400)
    
    # Postavljamo cookie kako bismo znali tko je prijavljen
    odgovor = RedirectResponse(url="/admin", status_code=302)
    odgovor.set_cookie(key="servis_id", value=str(servis.id), httponly=True)
    return odgovor

# --- ADMIN PANEL - Sada filtrira podatke prema prijavljenom servisu ---
@app.get("/admin", response_class=HTMLResponse)
def prikaži_glavni_admin_panel(
    request: Request, 
    servis_id: Optional[str] = Cookie(None), 
    db: Session = Depends(get_db)
):
    if not servis_id:
        return RedirectResponse(url="/login", status_code=302)
    
    # Dohvaćamo točno onaj servis koji je prijavljen preko Cookie-ja
    servis = db.query(Servis).filter(Servis.id == int(servis_id)).first()
    if not servis:
        return RedirectResponse(url="/login", status_code=302)
    
    # Statistika isključivo za OVAJ servis
    stat_zaprimljeno = db.query(ServisniNalog).filter(
        ServisniNalog.servis_id == servis.id, 
        ServisniNalog.status == "zaprimljeno"
    ).count()
    
    stat_radu = db.query(ServisniNalog).filter(
        ServisniNalog.servis_id == servis.id, 
        ServisniNalog.status == "u_radu"
    ).count()
    
    zavrseni_nalozi = db.query(ServisniNalog).filter(
        ServisniNalog.servis_id == servis.id, 
        ServisniNalog.status == "zavrseno"
    ).all()
    
    stat_profit = sum(nalog.profit for nalog in zavrseni_nalozi if hasattr(nalog, 'profit') and nalog.profit)

    # Dohvaćamo naloge samo za ovaj servis
    svi_nalozi = db.query(ServisniNalog).filter(ServisniNalog.servis_id == servis.id).order_by(ServisniNalog.id.desc()).all()

    return templates.TemplateResponse(
        "admin.html", 
        {
            "request": request, 
            "servis": servis,
            "stat_zaprimljeno": stat_zaprimljeno,
            "stat_radu": stat_radu,
            "stat_profit": stat_profit,
            "nalozi": svi_nalozi  
        }
    )

# --- AŽURIRANJE NALOGA ---
@app.post("/admin/azuriraj-nalog/{nalog_id}")
def azuriraj_status_naloga(
    nalog_id: int,
    status: str = Form(...),
    dogovorena_cijena: float = Form(...),
    profit: float = Form(...),
    servis_id: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    if not servis_id:
        return RedirectResponse(url="/login", status_code=302)

    # Sigurnosna provjera: nalog mora pripadati servisu koji ga pokušava mijenjati
    nalog = db.query(ServisniNalog).filter(
        ServisniNalog.id == nalog_id, 
        ServisniNalog.servis_id == int(servis_id)
    ).first()
    
    if not nalog:
        return HTMLResponse(content="<h3>Nalog nije pronađen ili nemate ovlasti!</h3>", status_code=403)
    
    stari_status = nalog.status
    nalog.status = status
    nalog.dogovorena_cijena = dogovorena_cijena
    nalog.profit = profit
    db.commit()

    if stari_status != status and nalog.klijent:
        pošalji_email_obavijest(
            primatelj_email=nalog.klijent.email,
            ime_klijenta=nalog.klijent.ime_prezime,
            token=nalog.tracking_token,
            novi_status=status,
            brand=nalog.brand,
            model=nalog.model_uredjaja
        )

    return RedirectResponse(url="/admin", status_code=303)

# --- ODJAVA (Briše Cookie) ---
@app.get("/logout")
def izvrši_odjavu(response: Response):
    odgovor = RedirectResponse(url="/login", status_code=302)
    odgovor.delete_cookie(key="servis_id")
    return odgovor

# --- JAVNA PRIJAVA POPRAVKA (ZA KORISNIKE) ---
@app.get("/prijava-popravka", response_class=HTMLResponse)
def prikaži_formu_prijave(request: Request):
    return templates.TemplateResponse("prijava_popravka.html", {"request": request})

@app.post("/prijava-popravka")
def izvrši_slanje_prijave(
    ime_prezime: str = Form(...),
    broj_telefona: str = Form(...),
    email: str = Form(...),
    brand: str = Form(...),
    model_uredaja: str = Form(...),  
    opis_kvara: str = Form(...),
    oprema: Optional[List[str]] = Form(default=None),  
    db: Session = Depends(get_db)
):
    try:
        # Kod javne prijave privremeno vežemo za prvi servis ili se može doraditi kroz URL (npr. /prijava-popravka?servis=1)
        servis = db.query(Servis).first()
        if not servis:
            return HTMLResponse(content="<h3>Sustav trenutno nema registriranih servisa.</h3>", status_code=400)

        klijent = db.query(Klijent).filter(Klijent.email == email).first()
        if not klijent:
            klijent = Klijent(
                servis_id=servis.id,  
                ime_prezime=ime_prezime, 
                broj_telefona=broj_telefona, 
                email=email
            )
            db.add(klijent)
            db.commit()
            db.refresh(klijent)

        if oprema and isinstance(oprema, list):
            tekst_opreme = ", ".join(oprema)
            puni_opis = f"{opis_kvara} | 🎒 Oprema: {tekst_opreme}"
        elif oprema:
            puni_opis = f"{opis_kvara} | 🎒 Oprema: {oprema}"
        else:
            puni_opis = f"{opis_kvara} | 🎒 Oprema: Bez opreme"

        generirani_token = str(uuid.uuid4())[:8]

        novi_nalog = ServisniNalog(
            servis_id=servis.id,
            klijent_id=klijent.id,
            tracking_token=generirani_token,
            brand=brand,
            model_uredjaja=model_uredaja,  
            serijski_imei="Nije navedeno",  
            opis_kvara=puni_opis,
            status="zaprimljeno",
            dogovorena_cijena=0.0,
            profit=0.0
        )
        
        db.add(novi_nalog)
        db.commit()
        
        return HTMLResponse(
            content="""
            <div style='text-align: center; margin-top: 50px; font-family: sans-serif;'>
                <h2 style='color: #16a34a;'>✓ Uspješno zaprimljeno!</h2>
                <p>Vaš zahtjev je poslan servisu. Javit ćemo Vam se ubrzo.</p>
                <a href='/prijava-popravka' style='color: #2563eb; text-decoration: none;'>Natrag na formu</a>
            </div>
            """, 
            status_code=200
        )
    except Exception as greška:
        return HTMLResponse(
            content=f"""
            <div style='text-align: center; margin-top: 50px; font-family: sans-serif; color: #dc2626;'>
                <h2>Greška prilikom spremanja u bazu podataka! ❌</h2>
                <p><strong>Detalji:</strong> {str(greška)}</p>
            </div>
            """,
            status_code=500
        )
    # --- SUPER ADMIN PANEL (UPRAVLJANJE REGISTRACIJAMA) ---

# --- SIGURNOSNA PROVJERA ZA SUPER ADMINA (BASIC AUTH) ---
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

SUPER_ADMIN_USER = "admin"           # Tvoje master korisničko ime
SUPER_ADMIN_PASS = "ZgMaster2026!"   # Tvoja jaka master lozinka (promijeni po želji)

def provjeri_super_admin_ovlasti(credentials: HTTPBasicCredentials = Depends(security)):
    ispravan_user = secrets.compare_digest(credentials.username, SUPER_ADMIN_USER)
    ispravna_lozinka = secrets.compare_digest(credentials.password, SUPER_ADMIN_PASS)
    if not (ispravan_user and ispravna_lozinka):
        raise HTTPException(
            status_code=401,
            detail="Krivo master korisničko ime ili lozinka!",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- SUPER ADMIN PANEL (SADA ZAŠTIĆEN) ---

@app.get("/super-admin", response_class=HTMLResponse)
def prikaži_super_admin_panel(
    request: Request, 
    db: Session = Depends(get_db),
    _username: str = Depends(provjeri_super_admin_ovlasti) # 🔥 Ova linija traži login!
):
    svi_servisi = db.query(Servis).order_by(Servis.id.desc()).all()
    
    statistika_servisa = []
    for s in svi_servisi:
        broj_naloga = db.query(ServisniNalog).filter(ServisniNalog.servis_id == s.id).count()
        statistika_servisa.append({
            "podaci": s,
            "broj_naloga": broj_naloga
        })

    return templates.TemplateResponse(
        "super_admin.html", 
        {
            "request": request, 
            "servisi": statistika_servisa
        }
    )

@app.post("/super-admin/obrisi-servis/{servis_id}")
def obrisi_servis_iz_sustava(
    servis_id: int, 
    db: Session = Depends(get_db),
    _username: str = Depends(provjeri_super_admin_ovlasti) # 🔥 Zaštita i na brisanju!
):
    servis = db.query(Servis).filter(Servis.id == servis_id).first()
    if not servis:
        return HTMLResponse(content="<h3>Servis nije pronađen!</h3>", status_code=404)
    
    # Prvo brišemo njegove naloge i klijente zbog integriteta baze
    db.query(ServisniNalog).filter(ServisniNalog.servis_id == servis_id).delete()
    db.query(Klijent).filter(Klijent.servis_id == servis_id).delete()
    
    # Na kraju brišemo sam servis
    db.delete(servis)
    db.commit()
    
    return RedirectResponse(url="/super-admin", status_code=303)