function check_est(val) {
    if (val == "all")
        jQuery(".est-individual").prop("checked", false);
    else
        jQuery("#est-all").prop("checked", false);
}
function check_sst(val) {
    if (val == "all")
        jQuery(".sst-individual").prop("checked", false);
    else
        jQuery("#sst-all").prop("checked", false);
}
jQuery(function() {
    jQuery("#u-start,#u-end").change(function() {
        jQuery("#s-start,#s-end").val("");
    });
    jQuery("#s-start,#s-end").change(function() {
        jQuery("#u-start,#u-end").val("");
    });
});
