#----------------------------------------------------------------------
# Form for editing PDQ data partner contact records.
# JIRA::OCECDR-4025
#----------------------------------------------------------------------
from pdq_data_partner import Product, Org, Contact, Control

class ContactEditingPage(Control):
    def __init__(self):
        Control.__init__(self, "Edit PDQ Data Partner Contact")
        self.contact_id = self.fields.getvalue("id") or ""
        self.org = self.fields.getvalue("org") or ""
        self.orgs = Org.picklist()
        self.buttons = (self.SAVE, self.CANCEL, self.ADMINMENU, self.LOG_OUT)
        self.validate_unsigned_int(self.org)
        self.validate_unsigned_int(self.contact_id)
    def run(self):
        if self.request == self.CANCEL:
            if self.org:
                self.parms["id"] = self.org
                url = Org.EDIT
            else:
                url = self.MANAGE
            self.navigate_to(url)
        else:
            Control.run(self)
    def populate_form(self, form):
        contact = Contact.load(self.contact_id)
        form.add_hidden_field("contact_id", self.contact_id)
        form.add_hidden_field("caller", self.get_referer())
        form.add_hidden_field("included", self.included)
        form.add_hidden_field("product", self.product)
        form.add_hidden_field("org", self.org)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Identification"))
        partner_id = contact and contact.org_id or self.org
        if partner_id:
            partner_id = int(partner_id)
        form.add_select("org_id", "Partner", self.orgs, default=partner_id)
        self.add_field(form, contact, "person_name", "Name")
        self.add_field(form, contact, "email_addr", "Email")
        self.add_field(form, contact, "phone", "Phone")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Notification History"))
        self.add_field(form, contact, "notif_count", "Count")
        self.add_field(form, contact, "notif_date", "Latest")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Contact Type"))
        for ct in Contact.TYPE_LABELS:
            if contact and contact.contact_type:
                checked = contact.contact_type == ct[0]
            else:
                checked = ct == "Primary"
            form.add_radio("contact_type", ct, ct[0], checked=checked)
        form.add("</fieldset>")
    def save(self):
        fv = Contact.FormValues(self.fields)
        if not fv.key and not fv.values["notif_count"]:
            fv.values["notif_count"] = "0"
        org_ids = [str(org_id) for org_id, org_name in self.orgs]
        fv.check_value("org_id", ftype=org_ids)
        fv.check_value("person_name")
        fv.check_value("email_addr", ftype="email")
        fv.check_value("phone", 64, required=False)
        fv.check_value("notif_count", ftype="uint")
        fv.check_value("contact_type", ftype=set(Contact.TYPES))
        fv.check_value("notif_date", ftype="datetime", required=False)
        Contact.save(fv)
        self.navigate_to(self.MANAGE)
        if self.org:
            self.parms["id"] = self.org
            url = Org.EDIT
        else:
            url = self.MANAGE
        self.navigate_to(url)
ContactEditingPage().run()
