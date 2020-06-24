function check_types(type) {
    console.log("type=" + type);
    switch (type) {
        case "C":
            jQuery("#types-c").prop("checked", true);
            jQuery(".specific-comment-types").prop("checked", false);
            break;
        case "R":
            break;
        default:
            jQuery("#types-c").prop("checked", false);
            break;
    }
    if (jQuery("#types-block input:checked").length < 1) {
        jQuery("#types-e").prop("checked", true);
        jQuery("#types-r").prop("checked", true);
    }
}

function check_selection_method(method) {
    switch (method) {
        case "id":
            jQuery(".by-board-block").hide();
            jQuery(".by-id-block").show();
            jQuery(".by-title-block").hide();
            break;
        case "board":
            jQuery(".by-board-block").show();
            jQuery(".by-id-block").hide();
            jQuery(".by-title-block").hide();
            break;
        case "title":
            jQuery(".by-board-block").hide();
            jQuery(".by-id-block").hide();
            jQuery(".by-title-block").show();
            break;
    }
}

jQuery(function() {
    var value = jQuery("input[name='selection_method']:checked").val();
    check_selection_method(value);
});
