function check_selection_method(value) {
    var methods = ["global", "specific"];
    var method = jQuery("input[name='selection_method']:checked").val();
    if (!methods.includes(method)) {
        jQuery("#selection_method-specific").prop("checked", false);
        jQuery("#selection_method-global").prop("checked", true);
        method = "global";
    }
    if (method == "global") {
        jQuery("#global-block").show();
        jQuery("#specific-block").hide();
        jQuery("#doctype-block").hide();
        jQuery(".by-board-block").hide();
        jQuery("#id-block").hide();
    }
    else {
        jQuery("#global-block").hide();
        jQuery("#specific-block").show();
        check_specific();
    }
}

function check_specific(value) {
    var options = ["doctype", "summary", "docid"];
    var specific = jQuery("input[name='specific']:checked").val();
    if (!options.includes(specific)) {
        jQuery("#specific-docid").prop("checked", false);
        jQuery("#specific-summary").prop("checked", false);
        jQuery("#specific-doctype").prop("checked", true);
        specific = "doctype";
    }
    switch (specific) {
    case "summary":
        jQuery("#doctype-block").hide()
        jQuery(".by-board-block").show()
        jQuery("#id-block").hide()
        break;
    case "docid":
        jQuery("#doctype-block").hide()
        jQuery(".by-board-block").hide()
        jQuery("#id-block").show()
        break;
    default:
        jQuery("#doctype-block").show()
        jQuery(".by-board-block").hide()
        jQuery("#id-block").hide()
    }
}

function check_board(value) {
    var all_selector = "#" + name + "-all";
    var ind_selector = "#" + name + "-set .ind";
    if (value == "all") {
        if (jQuery("#board-all").prop("checked"))
            jQuery("#board-set .ind").prop("checked", false);
        else
            jQuery("#board-all").prop("checked", true);
    }
    else if (jQuery("#board-set .ind" + ":checked").length > 0)
        jQuery("#board-all").prop("checked", false);
    else
        jQuery("#board-all").prop("checked", true);
}

function check_global(value) {
    switch (value) {
    case "denied":
        jQuery("#global-en").prop("checked", false);
        jQuery("#global-es").prop("checked", false);
        break;
    default:
        jQuery("#global-denied").prop("checked", false);
    }
    if (jQuery("#global-block input:checked").length < 1)
        jQuery("#global-en").prop("checked", true);
}

jQuery(function() {
    check_selection_method();
});
