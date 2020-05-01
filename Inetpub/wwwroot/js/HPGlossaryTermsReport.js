function check_dictionary() {
    var type = $("#dictionary").find(":selected").text();
    if (type == "Genetics")
        $("#loe-wrapper").hide();
    else
        $("#loe-wrapper").show();
}
function check_type() {
    var type = $("#type").find(":selected").text();
    if (type == "List of Terms")
        $("#pronunciation-wrapper").hide();
    else
        $("#pronunciation-wrapper").show();
}
$(function() {
    $("#type").change(check_type);
    $("#dictionary").change(check_dictionary);
    check_type();
    check_dictionary();
});
