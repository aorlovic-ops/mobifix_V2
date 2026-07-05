from weasyprint import HTML
from fastapi.templating import Jinja2Templates
import os

templates = Jinja2Templates(directory="templates")

def create_ticket_pdf(nalog, klijent):
    # Generiraj HTML iz template-a
    html_content = templates.get_template("pdf_template.html").render(
        nalog=nalog,
        klijent=klijent
    )
    # Pretvori HTML u PDF
    return HTML(string=html_content).write_pdf()