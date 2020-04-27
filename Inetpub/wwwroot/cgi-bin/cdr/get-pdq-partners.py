#!/usr/bin/env python

"""
Identify the PDQ data partners

Used by the report on SFTP retrieval activity for the PDQ data.
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
        else:
            self.activated = get_text(root.find(self.PROD_ACT))
            self.deactivated = get_text(root.find(self.PROD_OFF))
            self.status = "S" if licensee_type == "special" else "A"
        self.username = get_text(root.find(self.USERNAME))
        if self.username is not None:
            self.username = self.normalize(self.username)
        self.key = self.status, self.name.lower()
    def __lt__(self, other):
        return self.key < other.key

    @staticmethod
    def normalize(me):
        if me is None:
            return ""
        return re.sub(r"\s+", " ", me).strip()

cursor = db.connect(user="CdrGuest").cursor()
query = db.Query("document d", "d.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where("t.name = 'Licensee'")
doc_ids = [row.id for row in query.execute(cursor).fetchall()]
partners = []
select = "SELECT xml FROM document WHERE id = ?"
for doc_id in doc_ids:
    cursor.execute(select, (doc_id,))
    try:
        xml = cursor.fetchone().xml
        root = etree.fromstring(xml.encode("utf-8"))
        partners.append(Partner(doc_id, root))
    except:
        raise
        pass
root = etree.Element("partners")
for partner in sorted(partners):
    contact = etree.SubElement(root, "org_id", oid=str(partner.doc_id))
    etree.SubElement(contact, "org_name").text = partner.name
    etree.SubElement(contact, "org_status").text = partner.status
    etree.SubElement(contact, "activated").text = partner.activated
    etree.SubElement(contact, "terminated").text = partner.deactivated
    etree.SubElement(contact, "ftp_userid").text = partner.username
xml = etree.tostring(root, pretty_print=True, encoding="unicode")
sys.stdout.buffer.write(f"""\
Content-type: text/xml

{xml}""".encode("utf-8"))
