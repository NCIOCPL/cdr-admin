function send_to_clipboard(ids, n) {
    var $temp = $("<input>");
    $("body").append($temp);
    $temp.val(ids).select();
    if (document.execCommand("copy")) {
        var what = n == 1 ? "1 leaf ID has" : n + " leaf IDs have";
        alert(what + " been copied to the clipboard.");
    }
    else {
        $("#clipboard textarea").text(ids);
        $("#clipboard").show();
        alert("IDs have been copied to the edit box at the bottom of " +
              "this page. You can type Control/Command+C now to copy " +
              "them to the clipboard.");
    }
    $temp.remove();
}


function toggle_node(event, id) {
    var node = $(id);
    if (node.hasClass("hide")) {
        node.removeClass("hide").children("ul").show();
        node.children("span").children("span.sign").text("-");
    }
    else {
        node.addClass("hide").children("ul").hide();
        node.children("span").children("span.sign").text("+");
    }
    event.stopPropagation();
}
