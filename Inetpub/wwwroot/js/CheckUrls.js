/**
 * Client-side scripting for the report on external URLs with problems.
 */

function check_set(name, val) {
    var all_selector = "#" + name + "-all";
    var ind_selector = "#" + name + "-set .ind";
    if (val == "all") {
        if (jQuery(all_selector).prop("checked"))
            jQuery(ind_selector).prop("checked", false);
        else
            jQuery(all_selector).prop("checked", true);
    }
    else if (jQuery(ind_selector + ":checked").length > 0)
        jQuery(all_selector).prop("checked", false);
    else
        jQuery(all_selector).prop("checked", true);
}

function check_board(board) { check_set("board", board); }

function check_method(method) {
    switch (method) {
        case "id":
            jQuery(".by-doctype-block").hide();
            jQuery(".by-board-block").hide();
            jQuery(".by-id-block").show();
            break;
        case "doctype":
            jQuery(".by-doctype-block").show();
            jQuery(".by-id-block").hide();
            check_doctype();
            break;
    }
}

function check_doctype(doctype) {
    if (jQuery("#doctype-summary").prop("checked") ||
            jQuery("#doctype-glossarytermconcept").prop("checked"))
        jQuery(".by-board-block").show();
    else
        jQuery(".by-board-block").hide();
    if (jQuery("#doctype-summary").prop("checked"))
        jQuery("#board-set").show();
    else
        jQuery("#board-set").hide();
}

function check_opts(setting) {
    if (setting == "quick") {
        if (jQuery("#opts-quick").prop("checked")) {
            jQuery("#throttle-block").show();
            jQuery("#email-block").hide();
        }
        else {
            jQuery("#throttle-block").hide();
            jQuery("#email-block").show();
        }
    }
}

function check_report_type(type) {
    if (type == "Broken URLs") {
        jQuery(".opts-redirects-wrapper").show();
        jQuery(".opts-show-all-wrapper").hide();
    }
    else {
        jQuery(".opts-redirects-wrapper").hide();
        jQuery(".opts-show-all-wrapper").show();
    }
}

jQuery(function() {
    check_method(jQuery("input[name='method']:checked").val());
    check_opts("quick");
    check_report_type(jQuery("input[name='report-type']:checked").val());
});
