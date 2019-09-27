#!/usr/bin/env python

"""
Admin interface for managing CDR configuration in the /etc directory.
"""

import os
import cdr
import cdrcgi

class Control(cdrcgi.Control):

    LOGNAME = "config-files"
    DIRECTORY = cdr.ETC.replace("/", os.path.sep)
    FIX_PERMISSIONS = f"{cdr.BASEDIR}/bin/fix-permissions.cmd"
    FIX_PERMISSIONS = FIX_PERMISSIONS.replace("/", os.path.sep)
    FILES = "apphosts.rc", "env.rc", "dbports", "dbpw", "pw", "tier.rc"

    def __init__(self):
        cdrcgi.Control.__init__(self, "CDR Settings")
        if not cdr.canDo(self.session, "SET_SYS_VALUE"):
            cddrcgi.bail("You are not authorized to use this tool")
        self.extra = ""

    @property
    def content(self):
        if not hasattr(self, "_content"):
            content = self.fields.getvalue("content", self.original)
            self._content = content.replace("\r", "")
        return self._content

    @property
    def filename(self):
        if not hasattr(self, "_filename"):
            self._filename = self.fields.getvalue("filename") or self.FILES[0]
            opts = dict(val_list=self.FILES, msg=cdrcgi.TAMPERING)
            cdrcgi.valParmVal(self.filename, **opts)
        return self._filename

    @property
    def filepath(self):
        return r"{}\cdr{}".format(self.DIRECTORY, self.filename)

    @property
    def original(self):
        if not hasattr(self, "_original"):
            with open(self.filepath, encoding="utf-8", newline="\n") as fp:
                self._original = fp.read()
        return self._original

    def populate_form(self, form):
        if self.extra:
            form.add(form.B.P(self.extra, form.B.CLASS("warning center")))
        form.add('<fieldset style="width: 750px">')
        form.add(form.B.LEGEND("Set file and values"))
        values = [(f, "cdr{}".format(f)) for f in self.FILES]
        opts = dict(default=self.filename, onchange="javascript:change_file()")
        form.add_select("filename", "File", values, **opts)
        content = self.content.replace("\n", cdrcgi.NEWLINE)
        opts = dict(classes="bigbox", value=content)
        form.add_textarea_field("content", "Values", **opts)
        rules = "height: 600px; width: 600px; font-family: monospace;"
        form.add_css("textarea.bigbox {{ {} }}".format(rules))
        form.add("</fieldset>")

    def show_report(self):
        if self.content.strip() and self.content != self.original:
            with open(self.filepath, "w", encoding="utf-8") as fp:
                fp.write(self.content)
            self.extra = "Saved new values for {}".format(self.filepath)
            cmd = r"{} {}".format(self.FIX_PERMISSIONS, self.filepath)
            result = cdr.run_command(cmd, merge_output=True)
            if result.returncode:
                self.extra = result.stdout or "Failure fixing permissions"
        else:
            self.extra = "File {} unchanged".format(self.filepath)
        self.show_form()

    def show_form(self):
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "subtitle": self.title,
            "session": self.session
        }
        opts = self.set_form_options(opts)
        form = cdrcgi.Page(self.PAGE_TITLE or "", **opts)
        form.add_script("""\
function change_file() {{
    var filename = jQuery("#filename option:selected").val();
    if (filename) {{
        var url = "/cgi-bin/cdr/{}?Session={}&filename=" + filename;
        window.location.href = url;
    }}
}}""".format(self.script, self.session))
        self.populate_form(form)
        form.send()

Control().run()
