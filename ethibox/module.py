from woob.capabilities.base import find_object
from woob.capabilities.bill import Bill, CapDocument, DocumentNotFound, DocumentTypes, Subscription
from woob.tools.backend import BackendConfig, Module
from woob.tools.value import ValueBackendPassword

from .browser import EthiboxBrowser

__all__ = ["EthiboxModule"]


class EthiboxModule(Module, CapDocument):
    NAME = "ethibox"
    DESCRIPTION = "Ethibox — Hébergement éthique d'applications libres"
    MAINTAINER = "Kevin GUERIN — ASVOLA"
    EMAIL = "kevin.guerin@asvola.fr"
    LICENSE = "LGPLv3+"
    VERSION = "3.7"

    CONFIG = BackendConfig(
        ValueBackendPassword("login", label="Email", masked=False),
        ValueBackendPassword("password", label="Mot de passe"),
    )

    BROWSER = EthiboxBrowser

    accepted_document_types = (DocumentTypes.BILL,)

    def create_default_browser(self):
        return self.create_browser(
            self.config["login"].get(),
            self.config["password"].get(),
        )

    def iter_subscription(self):
        return self.browser.iter_subscription()

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def get_document(self, _id):
        subid = _id.split(".")[0]
        sub = self.get_subscription(subid)
        return find_object(self.iter_documents(sub), id=_id, error=DocumentNotFound)

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        return self.browser.download_document(bill)
