#!/usr/bin/env python

"""Admin interface for managing CDR configuration in the /etc directory.
"""

from functools import cached_property
import os
import cdr
from cdrcgi import Controller


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
.usa-textarea { font-family: monospace; font-size: .9rem; height: 32rem; }
""")
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
            self.bail("You are not authorized to use this tool")
        if self.request == self.SAVE:
            try:
                self.save()
            except Exception as e:
                self.logger.exception("Failure saving")
                self.bail(str(e))
        else:
            Controller.run(self)

    def save(self):
        """Save the currently edited configuration file if changed."""

        stripped = self.content.strip().replace("\r", "")
        original = self.original.strip().replace("\r", "")
        self.logger.debug("stripped=%r", stripped)
        self.logger.debug("original=%r", original)
        if stripped and stripped != original:
            with open(self.filepath, "w", encoding="utf-8") as fp:
                fp.write(self.content)
            command = f"{self.FIX_PERMISSIONS} {self.filepath}"
            result = cdr.run_command(command, merge_output=True)
            if result.returncode:
                message = result.stdout or "Failure fixing permissions"
                self.alerts.append(dict(message=message, type="warning"))
            else:
                message = f"Saved new values for {self.filepath}"
                self.alerts.append(dict(message=message, type="success"))
        else:
            message = f"File {self.filepath} unchanged"
            self.alerts.append(dict(message=message, type="warning"))
        self.show_form()

    @cached_property
    def buttons(self):
        """This form uses a custom action button."""
        return [self.SAVE]

    @cached_property
    def content(self):
        """Current content of the configuration file being edited."""

        return self.fields.getvalue("content", self.original).replace("\r", "")

    @cached_property
    def filename(self):
        """Configuration file currently being edited."""

        filename = self.fields.getvalue("filename") or self.FILES[0]
        if filename not in self.FILES:
            self.bail()
        return filename

    @cached_property
    def filepath(self):
        """Where the current configuration file is stored."""
        return r"{}\cdr{}".format(self.DIRECTORY, self.filename)

    @cached_property
    def files(self):
        """Value/display pairs for the file picklist."""
        return [(name, f"cdr{name}") for name in self.FILES]

    @cached_property
    def original(self):
        """The unedited content for the current configuration file."""

        with open(self.filepath, encoding="utf-8", newline="\n") as fp:
            return fp.read()

    @cached_property
    def same_window(self):
        """Stay on the same browser tab for this form."""
        return self.buttons


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
