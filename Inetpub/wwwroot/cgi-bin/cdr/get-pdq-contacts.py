#!/usr/bin/env python

"""
Identify the active PDQ data partner contacts

Used by the scheduled job to notify partners of new PDQ data availability.
"""

import re
import sys
from lxml import etree
from cdr import get_text
from cdrapi import db


class Partner:
    INFO = "LicenseeInformation/"
    TYPE = INFO + "LicenseeType"
    NAME = INFO + "LicenseeNameInformation/OfficialName/Name"
    STATUS = INFO + "LicenseeStatus"
    DATES = INFO + "LicenseeStatusDates/"
    PROD_ACT = DATES + "ProductionActivation"
    PROD_OFF = DATES + "ProductionInactivation"
    TEST_ACT = DATES + "TestActivation"
    TEST_EXT = DATES + "TestExtension"
    TEST_OFF = DATES + "TestInactivation"
    USERNAME = "FtpInformation/UserName"

    def __init__(self, doc_id, root):
        self.doc_id = doc_id
        self.name = self.normalize(get_text(root.find(self.NAME)))
        licensee_type = get_text(root.find(self.TYPE), "").lower()
        status = get_text(root.find(self.STATUS), "").lower()
        if status.startswith("test"):
            self.activated = get_text(root.find(self.TEST_ACT))
            self.deactivated = get_text(root.find(self.TEST_OFF))
            self.status = "T"
        elif status:
            self.activated = get_text(root.find(self.PROD_ACT))
            self.deactivated = get_text(root.find(self.PROD_OFF))
            self.status = "S" if licensee_type == "special" else "A"
        else:
            self.status = self.activated = self.deactivated = None
        if "deactivated" in status:
            self.deactivated = True
        self.renewed = get_text(root.find(self.TEST_EXT))
        self.username = get_text(root.find(self.USERNAME))
        if self.username is not None:
            self.username = self.normalize(self.username)
        self.key = self.status, self.name.lower()
        self.contacts = []
        for node in root.findall("ContactPersons/ContactPerson"):
            contact = self.Contact(node)
            if contact.type in ("I", "P", "S") and contact.email:
                self.contacts.append(contact)

    def __lt__(self, other):
        return self.key < other.key

    @staticmethod
    def normalize(me):
        if me is None:
            return ""
        return re.sub(r"\s+", " ", me).strip()

    class Contact:
        def __init__(self, node):
            self.type = node.get("Type")
            self.name = Partner.normalize(get_text(node.find("ContactName")))
            self.id = self.email = None
            detail = node.find("ContactDetail")
            if detail is not None:
                self.id = detail.get("{cips.nci.nih.gov/cdr}id")
                self.email = get_text(detail.find("Email"), "").strip()


cursor = db.connect(user="CdrGuest").cursor()
query = db.Query("query_term", "doc_id")
query.where("path = '/Licensee/LicenseeInformation/LicenseeStatus'")
statuses = "Production-terminated", "Test-expired", "NA-Storefront"
query.where(query.Condition("value", statuses, "NOT IN"))
doc_ids = [row.doc_id for row in query.execute(cursor).fetchall()]
partners = []
select = "SELECT xml FROM document WHERE id = ?"
for doc_id in doc_ids:
    cursor.execute(select, (doc_id,))
    try:
        xml = cursor.fetchone().xml
        root = etree.fromstring(xml.encode("utf-8"))
        partner = Partner(doc_id, root)
        if partner.status and not partner.deactivated:
            partners.append(partner)
    except Exception:
        pass
fields = "email_addr", "MAX(notif_date) AS notif_date"
query = db.Query("data_partner_notification", *fields)
query.group("email_addr")
notif_dates = dict([tuple(row) for row in query.execute(cursor).fetchall()])
root = etree.Element("contacts")
for partner in sorted(partners):
    for contact in partner.contacts:
        pid = "{:d}_{}".format(partner.doc_id, contact.id)
        notified = notif_dates.get(contact.email.lower())
        if notified:
            notified = str(notified).split(".")[0]
        wrapper = etree.SubElement(root, "contact", pid=str(pid))
        etree.SubElement(wrapper, "product").text = "CDR"
        etree.SubElement(wrapper, "email_address").text = contact.email
        etree.SubElement(wrapper, "person_name").text = contact.name
        etree.SubElement(wrapper, "org_name").text = partner.name
        etree.SubElement(wrapper, "org_status").text = partner.status
        etree.SubElement(wrapper, "contact_type").text = contact.type
        etree.SubElement(wrapper, "activation_date").text = partner.activated
        etree.SubElement(wrapper, "renewal_date").text = partner.renewed
        etree.SubElement(wrapper, "notified_date").text = notified
        etree.SubElement(wrapper, "org_id").text = str(partner.doc_id)
xml = etree.tostring(root, pretty_print=True, encoding="unicode")
sys.stderr.buffer.write(f"""\
Content-type: text/xml

{xml}""".encode("utf-8"))
