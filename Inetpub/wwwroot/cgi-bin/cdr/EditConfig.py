#!/usr/bin/env python

"""Admin interface for managing CDR configuration in the /etc directory.
"""

import os
import cdr
from cdrcgi import Controller, bail

class Control(Controller):

    LOGNAME = "config-files"
    SUBTITLE = "CDR Settings"
    SAVE = "Save"
    DIRECTORY = cdr.ETC.replace("/", os.path.sep)
    FIX_PERMISSIONS = f"{cdr.BASEDIR}/bin/fix-permissions.cmd"
    FIX_PERMISSIONS = FIX_PERMISSIONS.replace("/", os.path.sep)
    FILES = "apphosts.rc", "env.rc", "dbports", "dbpw", "pw", "tier.rc"

    def populate_form(self, page):
        """Put up the form with two fields."""

        fieldset = page.fieldset("Choose File, Edit, Save")
        opts = dict(
            default=self.filename,
            onchange="change_file()",
            options=self.files,
        )
        fieldset.append(page.select("filename", **opts))
        textarea = page.textarea("content", value=self.content)
        textarea.set("spellcheck", "false")
        fieldset.append(textarea)
        page.form.append(fieldset)
        page.add_css("""\
xbody { background: #fcfcfc; }
fieldset { width: 750px; }
fieldset .labeled-field select, fieldset .labeled-field textarea {
    width: 600px;
}
textarea { height: 600px; font-family: monospace; font-size: 12px; }""")

        page.add_script(f"""\
function change_file() {{
    var url = "{self.script}?Session={self.session.name}&filename=";
    var filename = jQuery("#filename option:selected").val();
    if (filename)
        window.location.href = url + filename;
}}""")

    def run(self):
        """Override the top-level entry point, as this isn't a report."""

        if not self.session.can_do("SET_SYS_VALUE"):
            bail("You are not authorized to use this tool")
        if self.request == self.SAVE:
            try:
                self.save()
            except Exception as e:
                self.logger.exception("Failure saving")
                bail(str(e))
        else:
            Controller.run(self)

    def save(self):
        """Save the currently edited configuration file if changed."""

        classes = "info center"
        if self.content.strip() and self.content != self.original:
            with open(self.filepath, "w", encoding="utf-8") as fp:
                fp.write(self.content)
            message = f"Saved new values for {self.filepath}"
            command = f"{self.FIX_PERMISSIONS} {self.filepath}"
            result = cdr.run_command(command, merge_output=True)
            if result.returncode:
                message = result.stdout or "Failure fixing permissions"
                classes = "failure center"
        else:
            message = f"File {self.filepath} unchanged"
        page = self.form_page
        self.populate_form(page)
        header = page.body.find("form/header")
        if header is not None:
            header.addnext(page.B.P(message, page.B.CLASS(classes)))
        page.send()

    @property
    def buttons(self):
        """Provide a custom set of action buttons."""
        return self.SAVE, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def content(self):
        """Current content of the configuration file being edited."""

        if not hasattr(self, "_content"):
            content = self.fields.getvalue("content", self.original)
            self._content = content.replace("\r", "")
        return self._content

    @property
    def filename(self):
        """Configuration file currently being edited."""

        if not hasattr(self, "_filename"):
            self._filename = self.fields.getvalue("filename") or self.FILES[0]
            if self._filename not in self.FILES:
                bail()
        return self._filename

    @property
    def filepath(self):
        """Where the current configuration file is stored."""
        return r"{}\cdr{}".format(self.DIRECTORY, self.filename)

    @property
    def files(self):
        """Value/display pairs for the file picklist."""
        return [(name, f"cdr{name}") for name in self.FILES]

    @property
    def original(self):
        """The unedited content for the current configuration file."""

        if not hasattr(self, "_original"):
            with open(self.filepath, encoding="utf-8", newline="\n") as fp:
                self._original = fp.read()
        return self._original


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
