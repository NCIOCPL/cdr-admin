#!/usr/bin/env python

"""Manage the list of servers to which we push fresh glossary information.

The list of servers is used by the CDR scheduler when it assembles data
for finding glossary terms which can be marked up with links to glossary
popups. That data is serialized and sent to each of the servers on the
list managed by this script.
"""

from cdrcgi import Controller
from cdr import getControlGroup, updateCtl


class Control(Controller):

    SUBTITLE = "Manage Glossary Servers"
    GROUP = LOGNAME = "glossary-servers"
    ACTION = "MANAGE GLOSSARY SERVERS"
    PARAGRAPH = (
        "Use this form to manage which servers will receive nightly "
        "glossary updates from this CDR tier."
    )
    BULLETS = (
        "Provide an alias to be used for logging and reporting",
        "Each alias must be unique for this tier",
        "Specify the base URL for each server",
        "To add a server block, click on the green plus sign",
        "To remove a server, click on its red X icon",
        "Click the Submit button to save your changes"
    )
    CSS = (
        ".glossary-server-button { padding-left: 10px; }",
        "fieldset li { list-style: none; padding: 0px; margin-left: -1em; }",
        'fieldset li:before { content: "\\261E"; margin: 0 .5em; }',
    )
    JS = "/js/glossary-servers.js"

    def populate_form(self, page):
        """Show instructions and the current list of servers.

        Add a button for appending another server block. Make
        that button only appear in the last block.

        Pass:
            page - HTMLPage object where we put the fields
        """

        servers = self.servers
        page.form.append(page.hidden_field("num-servers", len(servers)))
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.PARAGRAPH))
        ul = page.B.UL()
        for bullet in self.BULLETS:
            ul.append(page.B.LI(bullet))
        fieldset.append(ul)
        page.form.append(fieldset)
        counter = 1
        a_opts = dict(label="Alias", classes="alias")
        u_opts = dict(label="URL")
        for alias in sorted(servers):
            fieldset = page.fieldset("Server")
            fieldset.set("class", "server-block")
            fieldset.set("id", f"server-block-{counter}")
            opts = dict(label="Alias", classes="alias", value=alias)
            fieldset.append(page.text_field(f"alias-{counter:d}", **opts))
            opts = dict(label="URL", value=servers[alias])
            fieldset.append(page.text_field(f"url-{counter:d}", **opts))
            page.form.append(fieldset)
            counter += 1
        page.add_css("\n".join(self.CSS))
        page.head.append(page.B.SCRIPT(src=self.JS))

    def show_report(self):
        """Store changes to the server list (if any) and redraw the form.

        This isn't really a report, so we override this method
        to determine the delta between the servers we started
        with and the servers found on the submitted form. We
        then re-route back to the form, displaying confirmation
        of the save. We only need to store the changes, rather
        than wiping out the rows and starting again.
        """

        if not self.session.can_do(self.ACTION):
            self.logger.error("Denied for session %r", self.session)
            cdrcgi.bail("You do not have {!r} permission".format(self.ACTION))
        num_servers = int(self.fields.getvalue("num-servers"))
        old = getControlGroup(self.GROUP)
        new = dict()
        urls = set()
        i = 1
        while i <= num_servers:
            url = self.fields.getvalue(f"url-{i:d}")
            alias = self.fields.getvalue(f"alias-{i:d}")
            if url and alias:
                if alias in new:
                    cdrcgi.bail(f"Duplicate alias {alias!r}")
                if not url.startswith("http"):
                    cdrcgi.bail(f"{url!r} is not an HTTP URL")
                url = url.strip("/")
                key = url.lower()
                if key in urls:
                    cdrcgi.bail("f{key!r} appears more than once")
                urls.add(key)
                new[alias] = url
            i += 1
        opts = dict(group=self.GROUP)
        for alias in new:
            url = new[alias]
            if url != old.get(alias):
                opts["name"] = alias
                opts["value"] = url
                opts["comment"] = "Stored by the glossary servers script."
                updateCtl(self.session.name, "Create", **opts)
        for alias in old:
            if alias not in new:
                opts["name"] = alias
                updateCtl(self.session.name, "Inactivate", **opts)
        self.subtitle = f"Glossary Servers Saved: {len(new):d}"
        s = "" if len(new) == 1 else "s"
        self.logger.info("%d server%s saved by %s", len(new), s, self.user)
        self.show_form()

    @property
    def buttons(self):
        """Customize the action buttons to add DEVMENU."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def servers(self):
        """Dictionary of name->URL mappings for the glossary servers.

        The servers are stored in the CDR control table.

        Each server gets a row in the table, with `GROUP` as the
        value of the `grp` column, and a unique alias for the server
        stored in the `name` column. The URL for the server is
        stored in the `val` column.

        If no servers are found in the table, then fetch the
        DRUPAL CMS with which this tier is associated, and
        use the alias "Primary" for the server.
        """

        group = getControlGroup(self.GROUP)
        if not group:
            server = self.session.tier.hosts.get("DRUPAL")
            group = dict(Primary="https://{}".format(server))
        return group

    @property
    def subtitle(self):
        """String displayed directly below the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Let the save routing show what it did.

        Pass:
            value - new value to be displayed
        """

        self._subtitle = value

    @property
    def user(self):
        """User account name string (for logging)."""
        return self.session.user_name


if __name__ == "__main__":
    """Don't run script if loaded as a module."""
    Control().run()
