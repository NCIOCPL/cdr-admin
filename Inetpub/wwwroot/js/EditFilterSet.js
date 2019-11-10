/**
 * Client-side support for assigning members to CDR filter sets.
 */

// Call this every time the filter set membership changes.
function check_members() {

    // If we have other members, remove the placeholder.
    let count = jQuery("#members li").length;
    if (count > 1)
        jQuery("#members .dummy").remove();

    // If the set of members is empty, add the placeholder.
    if (count < 1) {
        let dummy = '<li class="dummy">Add some members, please!</li>';
        jQuery("#members").append(dummy);
    }

    // Let the user remove a member from the set by double-clicking it.
    jQuery("#members li").dblclick(function() {
        jQuery(this).remove();
        check_members();
    });
}

// Update the 'members' hidden field and submit the form for saving the set.
function save() {
    var members = [];
    jQuery("#members li").each(function(index) {
        let name = jQuery(this).text();
        let type = jQuery(this).attr("class");
        members.push({name: name, type: type});
    });
    jQuery("input[name='members']").val(JSON.stringify(members));
    jQuery("input[name='Request']").val("Save Set");
    jQuery("form").submit();
}

// Run the initialization when the page has loaded.
jQuery(function() {

    // Let the user re-order and prune the set by dragging.
    jQuery("#members").sortable({
        over: function() { removeIntent = false; },
        out: function() { removeIntent = true; },
        beforeStop: function(event, ui) {
            if(removeIntent === true) {
                ui.item.remove();
                check_members()
            }
        }
    });

    // Let the user pull new members into the set.
    jQuery("#filters li, #sets li").draggable({
        connectToSortable: "#members",
        helper: "clone",
        revert: "invalid",
        stop: function() { check_members(); }
    });

    // Let the user add a member by double-clicking it.
    jQuery("ul, li").disableSelection();
    jQuery("#sets li, #filters li").dblclick(function() {
        jQuery("#members").append(jQuery(this).clone());
        check_members();
    });

    // Intercept the Save action.
    jQuery("input[value='Save Set']").click(save);

    // Make sure the set has at least a placeholder item.
    check_members();
});
