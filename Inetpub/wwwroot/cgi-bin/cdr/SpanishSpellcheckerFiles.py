#!/usr/bin/env python

"""Create spellcheck file (HP or Patient) to be used with XMetaL
   for spell checking Spanish documents with terms from the CDR
   database
"""

import sys
from cdrcgi import Controller
from pathlib import Path
from CreateDictionary import CreateDictionary


class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Create Spanish Spellcheck Files from Dictionary"
    LOGNAME = "SpanishSpellcheckerFiles"

    def populate_form(self, page):
        """Prompt for the type of file to be created (HP or patient).

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P("Select the audience for which to create the "
                                 "dictionary file and click the ",
                                 page.B.STRONG("Submit "),
                                 "button. When finished save the file locally "
                                 "and then copy it to the XMetaL dictionary "
                                 "location on the network at: "))
        fieldset.append(page.B.P(page.B.PRE(
                                 r"    OCPL\_Cross\CDR\STEDMANS")))
        fieldset.append(page.B.P("Overwrite one of the existing files "
                                 "(dict_hp.dic or dict_pat.dic) with the "
                                 "newly created HP or patient file."))
        fieldset.append(page.B.P(page.B.STRONG("Note: "),
                                 "The job for the patient file may take "
                                 "several minutes to complete!"))
        page.form.append(fieldset)

        fieldset = page.fieldset("Select Audience")
        label = "Health professional"
        opts = dict(value="hp", label=label)

        fieldset.append(page.radio_button("audience", **opts))
        opts = dict(value="patient", label="Patient", checked=True)

        fieldset.append(page.radio_button("audience", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Cycle back to the form."""

        opts = dict(audience=self.fields.getvalue("audience"))
        dictFile = CreateDictionary(opts).run()
        filename = Path(dictFile).name

        try:
            dict_bytes = Path(dictFile).open("rb").read()
        except Exception as e:
            self.logger.exception("error reading %s", filename)
            self.bail(e)

        sys.stdout.buffer.write(f"""\
Content-type: application/octet-stream
Content-Disposition: attachment; filename={filename}
Content-length: {len(dict_bytes)}

""".encode("utf-8"))
        sys.stdout.buffer.write(dict_bytes)
        sys.exit(0)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
