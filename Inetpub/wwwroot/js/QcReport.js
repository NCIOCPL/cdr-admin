function check_section(option) {
    if (jQuery("#section-images:checked").length > 0)
        jQuery("#image-versions-fieldset").show();
    else
        jQuery("#image-versions-fieldset").hide();
}
function check_comment(option) {
    if (option == "all") {
        if (jQuery("#comment-all:checked").length > 0)
            jQuery("#comment-options-box input").prop("checked", true);
        else
            jQuery("#comment-options-box input").prop("checked", false);
    }
    else
        jQuery("#comment-all").prop("checked", false);
}

