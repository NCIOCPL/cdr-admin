/**
 * Client-side scripting for managing scheduled jobs.
 */

// Insert buttons for adding/removing job options.
function add_buttons() {
    console.log("start add_buttons()")
    jQuery(".job-opt-button").remove();
    green_button().insertAfter(jQuery(".opt-name").last());
    jQuery(".opt-name").each(function(i) {
        red_button(i).insertAfter(jQuery(this));
    });
    console.log("done add_buttons()")
}

// Create a button which adds a new (empty) option block.
function green_button() {
    var span = jQuery("<span>", {class: "job-opt-button"});
    var img = jQuery("<img>", {
        src: "/images/add.gif",
        onclick: "add_option_block()",
        class: "clickable",
        title: "Add another option"
    });
    span.append(img);
    return span;
}

// Create a button which removes the option block it's in.
function red_button(i) {
    var span = jQuery("<span>", {class: "job-opt-button"});
    var img = jQuery("<img>", {
        src: "/images/del.gif",
        onclick: "remove_option(" + ++i + ")",
        class: "clickable",
        title: "Remove option"
    });
    span.append(img);
    return span;
}

// Add a new block, possibly with existing options.
function add_option_block(i, name, value) {
    var id = i ? i : jQuery(".opt-name").length + 1;
    var attrs = {class: "opt-block", id: "opt-block-" + id};
    var fieldset = jQuery("<fieldset>", attrs);
    fieldset.append(jQuery("<legend>Job Option</legend>"));
    fieldset.append(make_field("name", id, "Name", name));
    fieldset.append(make_field("value", id, "Value", value));
    //jQuery("form").append(fieldset);
    fieldset.insertBefore("#options-block")
    jQuery("input[name='num-opts']").val(id);
    console.log("num-opts is " + jQuery("input[name='num-opts']").val())
    if (!i) {
        add_buttons();
    }
}

// Delete an option block and recreate all the remaining blocks.
function remove_option(id) {
    console.log("removing block " + id);
    var blocks = collect_options(id);
    console.log(JSON.stringify(blocks));
    jQuery(".opt-block").remove();
    jQuery.each(blocks, function(i, block) {
        add_option_block(i + 1, block["name"], block["value"]);
    });
    add_buttons();
}

// Create a labeled form field, possibly with an existing value.
function make_field(name, id, label, value) {
    var id = "opt-" + name + "-" + id;
    var field = jQuery("<div>", {class: "labeled-field"});
    field.append(jQuery("<label>", {for: id, text: label}));
    field.append(jQuery("<input>", {
        class: "opt-" + name,
        name: id,
        id: id,
        value: value
    }));
    return field;
}

// Gather up all the value information so we can recreate the blocks.
// Leave out the block we're going to remove.
function collect_options(skip) {
    var num_options = jQuery("input[name='num-opts']").val();
    var options = [];
    for (var i = 1; i <= num_options; ++i) {
        if (i != skip) {
            var name = jQuery("#opt-name-" + i).val();
            var value = jQuery("#opt-value-" + i).val();
            options.push({name: name, value: value});
        }
    }
    return options;
}

// Add the red and green buttons when the page first loads.
jQuery(function() {
    add_buttons();
    jQuery("input[value='Run Job Now']").click(function(e) {
        if (confirm("Are you sure?"))
            return true;
        e.preventDefault();
    });
    jQuery("input[value='Delete Job']").click(function(e) {
        if (confirm("Are you sure?"))
            return true;
        e.preventDefault();
    });
});
