#----------------------------------------------------------------------
# User interface for managing contact information for PDQ data partners.
# JIRA::OCECDR-4023
#----------------------------------------------------------------------

# Custom/application-specific modules
from pdq_data_partner import Product, Org, Contact, Control

class PartnerLandingPage(Control):
    def __init__(self):
        Control.__init__(self, "Manage PDQ Data Partners")
        self.buttons = (Org.BUTTON, Product.BUTTON,
                        self.ADMINMENU, self.LOG_OUT)
    def populate_form(self, form):
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select Data Product"))
        for product in self.products:
            checked = product == self.product
            form.add_radio("product", product, product, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Set Partner Status Filtering"))
        for value in self.STATUSES:
            label = "%s Partners" % value.capitalize()
            checked = value == self.included
            form.add_radio("included", label, value, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        legend = "Data Partners (click to edit individual records)"
        form.add(form.B.LEGEND(legend))
        form.add("<ul id='partners'>")
        for partner in sorted(self.get_partners()):
            partner.show(form, self.parms)
        form.add("</ul>")
        form.add("</fieldset>")
        form.add_css(self.CSS)
        form.add_script("""\
function apply_filters(included, product) {
    var selector = "li.partner.prod-" + product;
    if (included != "all")
        selector += "." + included;
    jQuery("li.partner").hide();
    jQuery(selector).show()
}
function check_included(included) {
    var product = jQuery("input[name='product']:checked").val();
    apply_filters(included, product);
    jQuery("#partners a").each(function(i) {
        var a = jQuery(this);
        var href = a.attr("href");
        a.attr("href", href.replace(/included=[^&]*/, "included=" + included));
    });
}
function check_product(product) {
    var included = jQuery("input[name='included']:checked").val();
    apply_filters(included, product);
}
""")
PartnerLandingPage().run()
