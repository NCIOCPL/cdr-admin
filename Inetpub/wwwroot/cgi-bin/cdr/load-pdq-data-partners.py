#----------------------------------------------------------------------
# Import the file ftp_vendors.db used to notify PDQ partners via email.
# This script has a web interface so that it can be loaded without
# submitting a ticket to CBIIT. If the program is run again it
# recreates the table and loads everything again.
#
# JIRA::OCECDR-4024
#----------------------------------------------------------------------
import cdrdb
import cdrcgi
import pdq_data_partner

class Control(cdrcgi.Control):
    PRODUCTS = {
        "CDR": "Production data retrieved by external partners via FTP",
        "TEST": "Used for internal development and testing"
    }
    BOGUS_PRODUCTS = set(["C.R", "CXR"])
    def __init__(self):
        cdrcgi.Control.__init__(self, "Upload PDQ Partner Data")
        self.conn = cdrdb.connect()
        self.cursor = self.conn.cursor()
        self.pnames = None
        pnames = self.fields.getvalue("pnames", "").strip()
        if pnames:
            self.pnames = set([p.strip().upper() for p in pnames.split(",")
                               if p.strip()])
        if not self.pnames:
            self.pnames = set(self.PRODUCTS)
        #cdrcgi.bail(repr(self.pnames))
    def set_form_options(self, opts):
        opts["enctype"] = "multipart/form-data"
        return opts
    def populate_form(self, form):
        tip = "Comma-separated list of allowed products."
        pnames = ",".join(self.pnames)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("PDQ Data Partners"))
        form.add_text_field("data", "Data File", upload=True)
        form.add_text_field("pnames", "Products", value=pnames, tooltip=tip)
        form.add("</fieldset>")
    def show_report(self):
        self.drop_old_objects()
        self.create_new_objects()
        self.products = self.add_products()
        for contact in self.fetch_contacts():
            contact.load(self)
        cdrcgi.navigateTo(pdq_data_partner.Control.MANAGE, self.session)
    def drop_old_objects(self):
        for table, constraint in (
            ("pdq_contact", "chk_org_status"),
            ("pdq_contact", "chk_contact_type"),
            ("pdq_contact_old", "chk_org_status"),
            ("pdq_contact_old", "chk_contact_type"),
            ("data_partner_org", "chk_org_status"),
            ("data_partner_contact", "chk_contact_type"),
        ):
            try:
                query = "ALTER TABLE %s DROP CONSTRAINT %s" % (table,
                                                               constraint)
                self.cursor.execute(query)
                self.conn.commit()
            except Exception, e:
                continue
                cdrcgi.bail("%s %s: %s" % (table, constraint, e))
        for what, name in (
            ("VIEW", "pdq_contact"),
            ("TABLE", "data_partner_contact"),
            ("TABLE", "data_partner_org"),
            ("TABLE", "data_partner_product"),
            ("TABLE", "data_product"),
        ):
            try:
                query = "DROP %s %s" % (what, name)
                self.cursor.execute(query)
                self.conn.commit()
            except Exception, e:
                pass
    def create_new_objects(self):
        self.cursor.execute("""\
CREATE TABLE data_partner_product
    (prod_id INTEGER        NOT NULL IDENTITY PRIMARY KEY,
   prod_name VARCHAR(64)    NOT NULL UNIQUE,
   prod_desc NVARCHAR(2048)     NULL,
 inactivated DATE               NULL,
    last_mod DATETIME       NOT NULL)""")
        self.conn.commit()
        self.cursor.execute("""\
CREATE TABLE data_partner_org
     (org_id INTEGER        NOT NULL IDENTITY PRIMARY KEY,
    org_name NVARCHAR(255)  NOT NULL UNIQUE,
     prod_id INTEGER        NOT NULL REFERENCES data_partner_product,
  org_status CHAR(1)        NOT NULL
                            CONSTRAINT chk_org_status
                            CHECK (org_status IN ('A','T','S')),
   activated DATE           NOT NULL,
  terminated DATE               NULL,
     renewal DATE               NULL,
ftp_username VARCHAR(64)        NULL,
    last_mod DATETIME       NOT NULL)""")
        self.conn.commit()
        self.cursor.execute("""\
CREATE TABLE data_partner_contact
 (contact_id INTEGER       NOT NULL IDENTITY PRIMARY KEY,
      org_id INTEGER       NOT NULL REFERENCES data_partner_org,
 person_name NVARCHAR(255) NOT NULL,
  email_addr VARCHAR(64)   NOT NULL,
       phone VARCHAR(64)       NULL,
contact_type CHAR(1)       NOT NULL
                           CONSTRAINT chk_contact_type
                           CHECK (contact_type IN ('P','S','I','D')),
 notif_count INTEGER       NOT NULL,
  notif_date DATETIME          NULL,
    last_mod DATETIME      NOT NULL)""")
        self.conn.commit()
        self.cursor.execute("""\
CREATE VIEW pdq_contact AS
SELECT c.contact_id,
       p.prod_name,
       c.email_addr,
       c.person_name,
       o.org_name,
       c.phone,
       o.org_status,
       c.notif_count,
       c.contact_type,
       o.ftp_username,
       o.activated,
       o.terminated,
       o.renewal,
       CASE WHEN c.notif_date IS NULL THEN 'N' ELSE 'Y' END AS notified,
       c.notif_date,
       o.org_id,
       c.last_mod
  FROM data_partner_contact c
  JOIN data_partner_org o
    ON o.org_id = c.org_id
  JOIN data_partner_product p
    ON p.prod_id = o.prod_id""")
        self.conn.commit()
        for suffix in ("product", "contact", "org"):
            query = "GRANT SELECT ON data_partner_%s TO CdrGuest" % suffix
            self.cursor.execute(query)
        self.cursor.execute("GRANT SELECT ON pdq_contact TO CdrGuest")
        self.conn.commit()
    def add_products(self):
        products = {}
        for name in self.PRODUCTS:
            if name in self.pnames:
                products[name] = self.add_product(name, self.PRODUCTS[name])
        for name in self.pnames:
            if name not in products:
                products[name] = self.add_product(name)
        return products
    def add_product(self, name, desc=None):
        self.cursor.execute("""\
INSERT INTO data_partner_product (prod_name, prod_desc, last_mod)
     VALUES (?, ?, GETDATE())""", (name, desc))
        self.cursor.execute("SELECT @@IDENTITY")
        prod_id = self.cursor.fetchall()[0][0]
        self.conn.commit()
        return prod_id
    def fetch_contacts(self):
        data = self.read_file()
        contacts = []
        for line in data.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                fields = line.split(":", len(Contact.COLS) - 1)
                if len(fields) == len(Contact.COLS) and fields[0] != "PRODUCT":
                    contacts.append(Contact(self, *fields))
        return sorted(contacts)
    def read_file(self):
        if "data" in self.fields.keys():
            data = self.fields["data"]
            if data.file:
                bytes = []
                while True:
                    more_bytes = data.file.read()
                    if not more_bytes:
                        break
                    bytes.append(more_bytes)
            else:
                bytes = [data.value]
            if not bytes:
                cdrcgi.bail("Empty file")
            return "".join(bytes)
        else:
            self.show_form()

class Contact:
    """
    Represents a row from the legacy data file for data partner contact
    records. Contact types are Primary, Secondary, Internal, and Deleted.
    Records with munged product fields are marked as Deleted (i.e. inactive);
    no email notifications will be sent to those contacts. The legacy
    contact data were stored in a denormalized organization. This code
    normalizes the data.
    """
    DB_FILE = "ftp_vendors.db"
    COLS = ("product", "notified", "email_address", "person_name", "org_name",
            "phone", "org_status", "notified_count", "contact_type",
            "ftp_username", "password", "vendor_id", "activation_date",
            "termination_date", "renewal_date", "notif_date")
    def __init__(self, control, *cols):
        for i, name in enumerate(self.COLS):
            setattr(self, name, cols[i] or None)
        self.product = self.product.upper()
        if self.product in control.BOGUS_PRODUCTS:
            self.contact_type = "D"
            self.product = "CDR"
    def __cmp__(self, other):
        return cmp((self.product, self.org_name, self.person_name),
                   (other.product, other.org_name, other.person_name))
    def load(self, control):
        org = Org.get(control, self)
        control.cursor.execute("""\
INSERT INTO data_partner_contact (org_id, email_addr, person_name, phone,
                                  notif_count, contact_type, notif_date,
                                  last_mod)
     VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())""",
                   (org.org_id, self.email_address, self.person_name,
                    self.phone, self.notified_count,
                    self.contact_type, self.notif_date))
        control.conn.commit()


class Org:
    orgs = {}
    def __init__(self, org_id, contact):
        self.org_id = org_id
        self.org_name = contact.org_name
        self.activation_date = contact.activation_date
        self.renewal_date = contact.renewal_date
        self.termination_date = contact.termination_date
    @classmethod
    def get(cls, control, contact):
        """
        Find or create org record for this contact. Resolve conflicting dates.
        """
        key = contact.org_name.lower()
        org = cls.orgs.get(key)
        if not org:
            org = cls.orgs[key] = cls.load(control, contact)
        else:
            org.resolve_conflicting_dates(control, contact)
        return org
    @classmethod
    def load(cls, control, contact):
        "Make sure our product exists, then insert our row in the org table."
        prod_name = contact.product
        if prod_name not in control.products:
            control.products[prod_name] = control.add_product(prod_name)
        values = (contact.org_name, control.products[prod_name],
                  contact.org_status, contact.activation_date,
                  contact.termination_date, contact.renewal_date,
                  contact.ftp_username)
        control.cursor.execute("""\
INSERT INTO data_partner_org (org_name, prod_id, org_status, activated,
                              terminated, renewal, ftp_username, last_mod)
     VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())""", values)
        control.cursor.execute("SELECT @@IDENTITY")
        org_id = control.cursor.fetchall()[0][0]
        return cls(org_id, contact)
    def resolve_conflicting_dates(self, control, contact):
        for date, col in (
            ("activation", "activated"),
            ("renewal", "renewal"),
            ("termination", "terminated"),
        ):
            current = getattr(self, "%s_date" % date)
            new = getattr(contact, "%s_date" % date)
            if new and (not current or new > current):
                control.cursor.execute("""\
UPDATE data_partner_org
   SET %s = ?
 WHERE org_id = ?""" % col, (new, self.org_id))
                control.conn.commit()

#----------------------------------------------------------------------
# One entry point to rule them all.
#----------------------------------------------------------------------
Control().run()
