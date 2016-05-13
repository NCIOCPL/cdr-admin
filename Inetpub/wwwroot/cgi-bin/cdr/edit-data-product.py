#----------------------------------------------------------------------
# Form for editing PDQ data product types.
# JIRA::OCECDR-4025
#----------------------------------------------------------------------
from pdq_data_partner import Product, Org, Contact, Control

class ProductEditingPage(Control):
    def __init__(self):
        Control.__init__(self, "Edit PDQ Data Product")
        self.prod_id = self.fields.getvalue("id") or ""
        self.validate_unsigned_int(self.prod_id)
        self.buttons = (self.SAVE, self.CANCEL, self.ADMINMENU, self.LOG_OUT)
    def populate_form(self, form):
        product = Product.load(self.prod_id)
        form.add_hidden_field("included", self.included)
        form.add_hidden_field("product", self.product)
        form.add_hidden_field("prod_id", self.prod_id)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Product Information"))
        self.add_field(form, product, "prod_name", "Name")
        self.add_field(form, product, "prod_desc", "Description")
        self.add_field(form, product, "inactivated", "Inactivated", True)
        form.add("</fieldset>")
    def save(self):
        fv = Product.FormValues(self.fields)
        fv.check_value("prod_name", 64, ftype="name")
        fv.check_value("prod_desc", 2048, required=False)
        fv.check_value("inactivated", ftype="date", required=False)
        Product.save(fv)
        self.parms["product"] = fv.values["prod_name"]
        self.navigate_to(Product.MANAGE)
ProductEditingPage().run()
