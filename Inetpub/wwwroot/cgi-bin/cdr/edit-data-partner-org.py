#----------------------------------------------------------------------
# Form for editing PDQ data partner records.
# JIRA::OCECDR-4025
#----------------------------------------------------------------------
from pdq_data_partner import Product, Org, Contact, Control

class PartnerEditingPage(Control):
    def __init__(self):
        Control.__init__(self, "Edit PDQ Data Partner")
        self.org_id = self.fields.getvalue("id") or ""
        self.validate_unsigned_int(self.org_id)
        self.buttons = self.make_buttons()
    def make_buttons(self):
        buttons = [self.SAVE, self.CANCEL]
        if self.org_id:
            buttons.append(Contact.BUTTON)
        return buttons + [self.ADMINMENU, self.LOG_OUT]
    def populate_form(self, form):
        org = Org.load(self.org_id)
        default_prod_id = Product.names[self.product]
        values = {
            "org_name": org and org.org_name or "",
            "org_status": org and org.org_status or "A",
            "prod_id": str(org and org.prod_id or default_prod_id),
            "ftp_username": org and org.ftp_username or "",
        }
        for field in Org.HISTORY_FIELDS:
            value = org and getattr(org, field) or ""
            if value:
                value = str(value)[:10]
            elif not org and field == "activated":
                value = self.TODAY
            values[field] = value
        if self.org_id:
            self.parms["org"] = self.org_id

        form.add_script(self.make_script(values))
        form.add_hidden_field("included", self.included)
        form.add_hidden_field("product", self.product)
        form.add_hidden_field("org_id", self.org_id)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Identification"))
        form.add_text_field("org_name", "Name", value=values["org_name"])
        form.add_text_field("ftp_username", "FTP Account",
                            value=values["ftp_username"])
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Partner History"))
        for field in Org.HISTORY_FIELDS:
            form.add_date_field(field, field.capitalize(), value=values[field])
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Product"))
        for prod_id, prod_name in Product.picklist(Product.INACTIVATED):
            checked = str(prod_id) == values["prod_id"]
            form.add_radio("prod_id", prod_name, prod_id, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Partner Status"))
        for status in Org.STATUS_LABELS:
            checked = status[0] == values["org_status"]
            form.add_radio("org_status", status, status[0], checked=checked)
        form.add("</fieldset>")
        if org and org.contacts:
            form.add_css(self.CSS)
            form.add("<fieldset>")
            form.add(form.B.LEGEND("Partner Contacts (click to edit)"))
            form.add("<ul>")
            for contact in org.contacts:
                contact.show(form, self.parms)
            form.add("<ul>")
            form.add("</fieldset>")
    def save(self):
        fv = Org.FormValues(self.fields)
        prod_ids = [str(prod_id) for prod_id, prod_name in Product.picklist()]
        fv.check_value("prod_id", ftype=prod_ids)
        fv.check_value("org_name", ftype="name")
        fv.check_value("ftp_username", 64, required=False)
        fv.check_value("org_status", ftype=Org.STATUSES)
        fv.check_value("activated", ftype="date")
        fv.check_value("terminated", ftype="date", required=False)
        fv.check_value("renewal", ftype="date", required=False)
        Org.save(fv)
        self.parms["product"] = Product.ids[int(fv.values["prod_id"])]
        self.navigate_to(self.MANAGE)
PartnerEditingPage().run()
