import io
import re
from datetime import datetime

import requests as _requests

from woob.capabilities.bill import Bill, DocumentTypes, Subscription
from woob.exceptions import BrowserIncorrectPassword

# reportlab is available in the system Python environment
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.pdfgen import canvas as _canvas

API = "https://app.ethibox.fr"
BLUE = HexColor("#0057B7")
LIGHT = HexColor("#F5F8FF")


def _app_name(desc):
    m = re.search(r"1 × ([^(]+)", desc)
    return m.group(1).strip() if m else "Service"


def _generate_pdf(inv) -> bytes:
    """Génère un PDF de facture Ethibox à partir des données API."""
    buf = io.BytesIO()
    dt = datetime.fromtimestamp(inv["date"] / 1000)
    ttc = float(inv["total"])
    ht = round(ttc / 1.20, 2)
    tva = round(ttc - ht, 2)

    c = _canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    c.setFillColor(BLUE)
    c.rect(0, H - 35 * mm, W, 35 * mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(15 * mm, H - 20 * mm, "Ethibox")
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, H - 28 * mm, "Hébergement éthique d'applications libres")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(W - 15 * mm, H - 22 * mm, "FACTURE")

    c.setFillColor(LIGHT)
    c.rect(0, H - 60 * mm, W, 25 * mm, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15 * mm, H - 44 * mm, "N° Facture :")
    c.drawString(70 * mm, H - 44 * mm, "Date :")
    c.drawString(120 * mm, H - 44 * mm, "Statut :")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, H - 51 * mm, inv["number"])
    c.drawString(70 * mm, H - 51 * mm, dt.strftime("%d/%m/%Y"))
    c.setFillColor(HexColor("#1A8C3A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(120 * mm, H - 51 * mm, "✓ PAYÉE")

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(15 * mm, H - 75 * mm, "DE :")
    c.drawString(110 * mm, H - 75 * mm, "À :")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(["Ethibox SAS", "contact@ethibox.fr", "https://ethibox.fr"]):
        c.drawString(15 * mm, H - (82 + i * 6) * mm, line)
    for i, line in enumerate(["Kevin GUERIN – ASVOLA", "kevin.guerin@asvola.fr"]):
        c.drawString(110 * mm, H - (82 + i * 6) * mm, line)

    c.setStrokeColor(BLUE)
    c.setLineWidth(0.5)
    c.line(15 * mm, H - 110 * mm, W - 15 * mm, H - 110 * mm)

    c.setFillColor(BLUE)
    c.rect(15 * mm, H - 122 * mm, W - 30 * mm, 10 * mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(18 * mm, H - 118 * mm, "Description")
    c.drawRightString(W - 55 * mm, H - 118 * mm, "Montant HT")
    c.drawRightString(W - 30 * mm, H - 118 * mm, "TVA 20%")
    c.drawRightString(W - 15 * mm, H - 118 * mm, "Total TTC")

    c.setFillColor(LIGHT)
    c.rect(15 * mm, H - 133 * mm, W - 30 * mm, 10 * mm, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(18 * mm, H - 129 * mm, inv["description"])
    c.drawRightString(W - 55 * mm, H - 129 * mm, f"{ht:.2f} €")
    c.drawRightString(W - 30 * mm, H - 129 * mm, f"{tva:.2f} €")
    c.drawRightString(W - 15 * mm, H - 129 * mm, f"{ttc:.2f} €")

    c.setStrokeColor(BLUE)
    c.setLineWidth(1)
    c.rect(W - 80 * mm, H - 155 * mm, 65 * mm, 20 * mm, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(black)
    c.drawString(W - 78 * mm, H - 143 * mm, "TOTAL TTC :")
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - 17 * mm, H - 143 * mm, f"{ttc:.2f} €")
    c.setFillColor(black)
    c.setFont("Helvetica", 8)
    c.drawString(W - 78 * mm, H - 150 * mm, f"Dont TVA 20% : {tva:.2f} €")

    c.setFont("Helvetica", 8)
    c.setFillColor(grey)
    c.drawString(15 * mm, H - 165 * mm,
                 f"Payé par prélèvement SEPA le {dt.strftime('%d/%m/%Y')} — Stripe ID : {inv['id']}")

    c.setFillColor(BLUE)
    c.rect(0, 0, W, 15 * mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, 6 * mm,
                        "Ethibox — contact@ethibox.fr — https://ethibox.fr — Facture générée via API Stripe")
    c.save()
    return buf.getvalue()


class EthiboxBrowser:
    """Browser REST pour l'API Ethibox (génération PDF locale via reportlab)."""

    def __init__(self, username, password, *args, **kwargs):
        self.username = username
        self.password = password
        self._session = _requests.Session()
        self._session.headers.update({"User-Agent": "woob/3.7", "Accept": "application/json"})
        self._logged = False

    def _login(self):
        r = self._session.post(
            f"{API}/api/login",
            json={"email": self.username, "password": self.password},
            timeout=15,
        )
        if r.status_code != 200:
            raise BrowserIncorrectPassword("Identifiants Ethibox invalides")
        self._logged = True

    def _ensure_auth(self):
        if not self._logged:
            self._login()

    def iter_subscription(self):
        sub = Subscription()
        sub.id = "ethibox"
        sub.label = "Ethibox"
        sub.subscriber = self.username
        yield sub

    def iter_documents(self, subscription):
        self._ensure_auth()
        r = self._session.get(f"{API}/api/invoices", timeout=20)
        r.raise_for_status()
        for inv in r.json():
            dt = datetime.fromtimestamp(inv["date"] / 1000)
            bill = Bill()
            bill.id = f"ethibox.{inv['id']}"
            bill.date = dt.date()
            bill.label = inv["number"]
            bill.format = "pdf"
            bill.type = DocumentTypes.BILL
            bill.price = float(inv["total"])
            bill._inv_data = inv
            yield bill

    def download_document(self, bill):
        self._ensure_auth()
        inv = getattr(bill, "_inv_data", None)
        if inv is None:
            # Re-fetch if no cached data
            r = self._session.get(f"{API}/api/invoices", timeout=20)
            inv_id = bill.id.split(".")[-1]
            inv = next((i for i in r.json() if i["id"] == inv_id), None)
        if inv is None:
            raise Exception(f"Facture introuvable : {bill.id}")
        return _generate_pdf(inv)
