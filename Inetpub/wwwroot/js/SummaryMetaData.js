function check_method(method) {
    switch (method) {
    case "id":
        $("#doc-id-box").show();
        $("#doc-title-box").hide();
        $("#group-box").hide();
        break;
    case "title":
        $("#doc-id-box").hide();
        $("#doc-title-box").show();
        $("#group-box").hide();
        break;
    case "group":
        $("#doc-id-box").hide();
        $("#doc-title-box").hide();
        $("#group-box").show();
        break;
    }
}
$(function() {
    var method = $("input[name='method']:checked").val();
    check_method(method);
});
