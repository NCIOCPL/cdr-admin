from cdrcgi import Controller


class Control(Controller):

    LOGNAME = "error-404"
    SUBTITLE = "404: Not Found"
    TEXT = "Sorry, the resource which you requested cannot be located."

    def populate_form(self, page):
        """Tell the user what happened."""

        fieldset = page.fieldset("Page Not Found")
        fieldset.append(page.B.P(self.TEXT))
        page.body.append(fieldset)

    @property
    def buttons(self):
        """Don't provide any form buttons."""
        return []


Control().run()
