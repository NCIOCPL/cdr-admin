var next_counter = 0;
var descs = {"e": "linking element", "r": "custom rule"};
function add_block(n, t) {
    block = templates[t].replace(/@@COUNTER@@/g, next_counter);
    jQuery(block).insertAfter("#block-" + n);
    ++next_counter;
    console.log("next_counter bumped to " + next_counter);
}
function del_block(n, t) {
    if (confirm("Do you really want to delete this " + descs[t] + " block?")) {
        if (jQuery("." + t + "-block").length < 2)
            add_block(n, t);
        jQuery("#block-" + n).remove();
    }
}
jQuery(function() {
    var title = "Return to menu of link types";
    jQuery("h1 input[value='Cancel']").attr("title", title);
    jQuery("h1 input[value='Delete']").click(function(e) {
        if (confirm("Are you sure?"))
            return true;
        e.preventDefault();
    });
    next_counter = jQuery(".numbered-block").length + 1;
    console.log("next_counter starts at " + next_counter);
});
