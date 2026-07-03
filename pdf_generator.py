from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

def create_ticket_pdf(ticket_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Zaglavlje
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 800, f"Radni nalog: {ticket_data['ticket_number']}")
    
    # Podaci o klijentu
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Klijent: {ticket_data['customer_name']}")
    c.drawString(50, 755, f"Model uređaja: {ticket_data['device_model']}")
    
    # Opis kvara
    c.drawString(50, 725, "Opis kvara:")
    c.drawString(50, 710, ticket_data['description'])
    
    # Oprema (primjer za checkboxove)
    c.drawString(50, 680, "Dodatna oprema:")
    y = 665
    for item in ["Punjač", "Baterija", "Kutija"]:
        val = "Da" if ticket_data.get(item.lower()) else "Ne"
        c.drawString(70, y, f"- {item}: {val}")
        y -= 15
        
    c.save()
    buffer.seek(0)
    return buffer