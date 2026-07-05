@app.post("/prijava-popravka")
def zaprimi_popravak(
    ime_prezime: str = Form(...),
    broj_telefona: str = Form(...),
    email: str = Form(...),
    brand: str = Form(...),
    model_uredaja: str = Form(...),
    imei_sn: Optional[str] = Form(""),
    opis_kvara: str = Form(...),
    oprema: List[str] = Form(default=[]),
    # Dodana nova polja za checkboxove
    ostecen_ekran: int = Form(0),
    ostecenje_vlagom: int = Form(0),
    db: Session = Depends(get_db)
):
    # 1. Kreiranje klijenta
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

    # 2. Kreiranje servisnog naloga s novim poljima
    nalog = ServisniNalog(
        servis_id=ZADANI_SERVIS_ID, 
        klijent_id=klijent.id, 
        tracking_token=secrets.token_hex(3).upper(),
        brand=brand, 
        model_uredjaja=model_uredaja, 
        imei_sn=imei_sn,
        opis_kvara=prosireni_opis,
        status='zaprimljeno',
        napomena_servisera="",
        # Spremanje checkbox vrijednosti
        ostecen_ekran=ostecen_ekran,
        ostecenje_vlagom=ostecenje_vlagom
    )
    
    db.add(nalog)
    db.commit()
    
    return RedirectResponse(url="/admin", status_code=303)