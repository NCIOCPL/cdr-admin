#!/usr/bin/env python

"""
Manage the list of servers to which we push fresh glossary information

The list of servers is used by the CDR scheduler when it assembles data
for finding glossary terms which can be marked up with links to glossary
popups. That data is serialized and sent to each of the servers on the
list managed by this script.
"""

import cdr
import cdrcgi
from cdrapi.settings import Tier
from cdrapi.users import Session

class Control(cdrcgi.Control):
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

    def __init__(self):
        cdrcgi.Control.__init__(self, "Manage Glossary Servers")
        self.tier = Tier()
        self.user = Session(self.session).user_name
        self.buttons = self.SUBMIT, self.ADMINMENU, self.LOG_OUT

    @property
    def servers(self):
        """
        The servers are stored in the CDR control table

        Each server gets a row in the table, with `GROUP` as the
        value of the `grp` column, and a unique alias for the server
        stored in the `name` column. The URL for the server is
        stored in the `val` column.

        If no servers are found in the table, then fetch the
        DRUPAL CMS with which this tier is associated, and
        use the alias "Primary" for the server.
        """

        group = cdr.getControlGroup(self.GROUP)
        if not group:
            server = self.tier.hosts.get("DRUPAL")
            group = dict(Primary="https://{}".format(server))
        return group

    def show_report(self):
        """
        Store changes to the server list

        This isn't really a report, so we override this method
        to determine the delta between the servers we started
        with and the servers found on the submitted form. We
        then re-route back to the form, displaying confirmation
        of the save. We only need to store the changes, rather
        than wiping out the rows and starting again.
        """

        if not cdr.canDo(self.session, self.ACTION):
            self.logger.error("Denied for session %r", self.session)
            cdrcgi.bail("You do not have {!r} permission".format(self.ACTION))
        num_servers = int(self.fields.getvalue("num-servers"))
        old = cdr.getControlGroup(self.GROUP)
        new = dict()
        urls = set()
        i = 1
        while i <= num_servers:
            url = self.get_unicode_parameter("url-{:d}".format(i))
            alias = self.get_unicode_parameter("alias-{:d}".format(i))
            if url and alias:
                if alias in new:
                    cdrcgi.bail("Duplicate alias {!r}".format(alias))
                if not url.startswith("http"):
                    cdrcgi.bail("{!r} is not an HTTP URL".format(url))
                url = url.strip("/")
                key = url.lower()
                if key in urls:
                    cdrcgi.bail("{!r} appears more than once".format(key))
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
                cdr.updateCtl(self.session, "Create", **opts)
        for alias in old:
            if alias not in new:
                opts["name"] = alias
                cdr.updateCtl(self.session, "Inactivate", **opts)
        self.title = "Glossary Servers Saved: {:d}".format(len(new))
        s = "" if len(new) == 1 else "s"
        self.logger.info("%d server%s saved by %s", len(new), s, self.user)
        self.show_form()

    def populate_form(self, form):
        """
        Show instructions and the current list of servers

        Add a button for appending another server block. Make
        that button only appear in the last block.
        """

        servers = self.servers
        form.add_hidden_field("num-servers", str(len(servers)))
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Instructions"))
        form.add(form.B.P(self.PARAGRAPH))
        form.add("<ul>")
        for bullet in self.BULLETS:
            form.add(form.B.LI(bullet))
        form.add("</ul>")
        form.add("</fieldset>")
        counter = 1
        fieldset = '<fieldset class="server-block" id="server-block-{:d}">'
        for alias in sorted(servers):
            url = servers[alias]
            form.add(fieldset.format(counter))
            form.add(form.B.LEGEND("Server"))
            name = "alias-{:d}".format(counter)
            form.add_text_field(name, "Alias", value=alias, classes="alias")
            name = "url-{:d}".format(counter)
            form.add_text_field(name, "URL", value=url)
            form.add("</fieldset>")
            counter += 1
        form.add_css("""\
.glossary-server-button { padding-left: 10px; }
fieldset li { list-style: none; padding: 0px; margin-left: -1em; }
fieldset li:before { content: "\\261E"; margin: 0 .5em; }
""")
        form.add_script("""\
// Insert buttons for adding/removing server blocks.
function add_buttons() {
    jQuery(".glossary-server-button").remove();
    green_button().insertAfter(jQuery(".alias").last());
    jQuery(".alias").each(function(i) {
        red_button(i).insertAfter(jQuery(this));
    });
}

// Create a button which adds a new (empty) server block.
function green_button() {
    var span = jQuery("<span>", {class: "glossary-server-button"});
    var img = jQuery("<img>", {
        src: "/images/add.gif",
        onclick: "add_server_block()",
        class: "clickable",
        title: "Add another server"
    });
    span.append(img);
    return span;
}

// Create a button which removes the server block it's in.
function red_button(i) {
    var span = jQuery("<span>", {class: "glossary-server-button"});
    var img = jQuery("<img>", {
        src: "/images/del.gif",
        onclick: "remove_server(" + ++i + ")",
        class: "clickable",
        title: "Remove server"
    });
    span.append(img);
    return span;
}

// Add a server block, possibly with existing values.
function add_server_block(i, alias, url) {
    var id = i ? i : jQuery(".alias").length + 1;
    var attrs = {class: "server-block", id: "server-block-" + id};
    var fieldset = jQuery("<fieldset>", attrs);
    fieldset.append(jQuery("<legend>Server</legend>"));
    fieldset.append(make_field("alias", id, "Alias", alias));
    fieldset.append(make_field("url", id, "URL", url));
    jQuery("form").append(fieldset);
    jQuery("input[name='num-servers']").val(id);
    if (!i) {
        add_buttons();
    }
}

// Delete a server block and recreate all the remaining blocks.
function remove_server(id) {
    console.log("removing block " + id);
    var blocks = collect_servers(id);
    console.log(JSON.stringify(blocks));
    jQuery(".server-block").remove();
    jQuery.each(blocks, function(i, server) {
        add_server_block(i + 1, server["alias"], server["url"]);
    });
    add_buttons();
}

// Create a labeled form field, possibly with an existing value.
function make_field(name, id, label, value) {
    var id = name + "-" + id;
    var field = jQuery("<div>", {class: "labeled-field"});
    field.append(jQuery("<label>", {for: id, text: label}));
    field.append(jQuery("<input>", {
        class: name,
        name: id,
        id: id,
        value: value
    }));
    return field;
}

// Gather up all the server information so we can recreate the blocks.
// Leave out the block we're going to remove.
function collect_servers(skip) {
    var num_servers = jQuery("input[name='num-servers']").val();
    var servers = [];
    for (var i = 1; i <= num_servers; ++i) {
        if (i != skip) {
            var url = jQuery("#url-" + i).val();
            var alias = jQuery("#alias-" + i).val();
            servers.push({alias: alias, url: url});
        }
    }
    return servers;
}

// Add the red and green buttons when the page first loads.
jQuery(add_buttons());
""")

Control().run()
