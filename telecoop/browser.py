from datetime import datetime

import requests as _requests

from woob.capabilities.bill import Bill, DocumentTypes, Subscription
from woob.exceptions import BrowserIncorrectPassword

API = "https://espace-personnel-api.telecoop.fr"


class TelecoopBrowser:
    """Browser REST minimaliste pour l'API TeleCoop."""

    def __init__(self, username, password, *args, **kwargs):
        self.username = username
        self.password = password
        self._token = None
        self._session = _requests.Session()
        self._session.headers.update({"User-Agent": "woob/3.7", "Accept": "application/json"})

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _login(self):
        r = self._session.post(
            f"{API}/api/customer/login",
            json={"email": self.username, "password": self.password},
            timeout=15,
        )
        if r.status_code != 200 or "token" not in r.json():
            raise BrowserIncorrectPassword("Identifiants Telecoop invalides")
        self._token = r.json()["token"]
        self._session.headers["Authorization"] = f"Bearer {self._token}"

    def _ensure_auth(self):
        if not self._token:
            self._login()

    # ── CapDocument ───────────────────────────────────────────────────────────

    def iter_subscription(self):
        sub = Subscription()
        sub.id = "telecoop"
        sub.label = "TeleCoop"
        sub.subscriber = self.username
        yield sub

    def iter_documents(self, subscription):
        self._ensure_auth()
        seen = set()
        page = 1
        while True:
            r = self._session.get(f"{API}/api/customer/invoices", params={"page": page}, timeout=20)
            r.raise_for_status()
            body = r.json()
            items = body.get("data", [])
            meta = body.get("meta", {})

            for inv in items:
                if inv["id"] in seen:
                    continue
                seen.add(inv["id"])
                try:
                    dt = datetime.strptime(inv["formatted_created"], "%d/%m/%Y")
                except ValueError:
                    continue

                bill = Bill()
                bill.id = f"telecoop.{inv['id']}"
                bill.date = dt.date()
                bill.label = inv["ident"]
                bill.format = "pdf"
                bill.type = DocumentTypes.BILL
                bill._inv_id = inv["id"]
                bill._ident = inv["ident"]
                yield bill

            if page >= meta.get("nbpages", 1):
                break
            page += 1

    def download_document(self, bill):
        self._ensure_auth()
        inv_id = getattr(bill, "_inv_id", None) or bill.id.split(".")[-1]
        r = self._session.get(f"{API}/api/customer/invoices/{inv_id}", timeout=30)
        r.raise_for_status()
        return r.content
