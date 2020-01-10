/**
 * Client-side scripting for managing glossifier servers.
 */

// Insert buttons for adding/removing server blocks.
function add_buttons() {
    console.log("start add_buttons()")
    jQuery(".glossary-server-button").remove();
    green_button().insertAfter(jQuery(".alias").last());
    jQuery(".alias").each(function(i) {
        red_button(i).insertAfter(jQuery(this));
    });
    console.log("done add_buttons()")
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
jQuery(function() {
    add_buttons();
});
