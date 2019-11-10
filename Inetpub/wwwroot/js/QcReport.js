function check_section(option) {
    if (jQuery("#section-images:checked").length > 0)
        jQuery("#image-versions-fieldset").show();
    else
        jQuery("#image-versions-fieldset").hide();
}

