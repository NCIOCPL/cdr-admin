#----------------------------------------------------------------------
# User interface for managing PDQ data products.
# JIRA::OCECDR-4023
#----------------------------------------------------------------------

# Custom/application-specific modules
from pdq_data_partner import Product, Org, Contact, Control

class ProductLandingPage(Control):
    def __init__(self):
        Control.__init__(self, "Manage PDQ Data Products")
        self.buttons = (Product.CREATE, self.BUTTON,
                        self.ADMINMENU, self.LOG_OUT)
    def populate_form(self, form):
        form.add_hidden_field("included", self.included)
        form.add_hidden_field("product", self.product)
        form.add("<fieldset>")
        legend = "Data Products (click to edit individual records)"
        form.add(form.B.LEGEND(legend))
        form.add("<ul>")
        for product in sorted(Product.products):
            product.show(form, self.parms)
        form.add("</ul>")
        form.add("</fieldset>")
        form.add_css(self.CSS)
ProductLandingPage().run()
