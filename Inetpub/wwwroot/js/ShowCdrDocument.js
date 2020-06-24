function check_selection_method(method) {
    switch (method) {
        case "id":
            jQuery("#by-id-block").show();
            jQuery("#by-title-block").hide();
            break;
        case "title":
            jQuery("#by-id-block").hide();
            jQuery("#by-title-block").show();
            break;
    }
}

function check_vtype(vtype) {
    if (vtype == "num")
        jQuery("#version-number-block").show();
    else
        jQuery("#version-number-block").hide();
}

jQuery(function() {
    var val = jQuery("input[name='selection_method']:checked").val();
    check_selection_method(val);
    check_vtype(jQuery("input[name='vtype']:checked").val());
});
