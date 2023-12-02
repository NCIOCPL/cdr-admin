/* Client-side scripting for QC report forms. */

function toggle_alternate_comment_options() {

    // Show/hide the parallel set of comment checkboxes.
    var el = document.getElementById("alternate-comment-options");
    var button = document.getElementById("show-options");
    console.log("el.style.display is " + el.style.display);
    if (!el.style.display || el.style.display == 'none') {
        el.style.display = 'block';
        button.textContent = "Hide Individual Options";
    }
    else {
        el.style.display = 'none';
        button.textContent = "Show Individual Options";
    }
}

function check_options(option) {

    console.log("checking option " + option);

    // If the user wants to see images, show the companion checkbox.
    if (option === "images") {
        var images = document.getElementById("options-images");
        var pub_images = document.getElementById('pub-images');
        if (images.checked == true) {
            pub_images.style.display = 'block';
        }
        else {
            pub_images.style.display = 'none';
        }
    }

    // Coordinate the two sets of checkboxes for controlling which
    // comments areto be displayed for summaries. This reproduces the
    // bugs in the original version, because the users are fond of those
    // bugs.
    else if (option === "com_all") {
        jQuery("#alternate-comment-options input").prop("checked", true);
        jQuery(".comgroup input").prop("checked", false);
        jQuery("#options-com-all").prop("checked", true);
    }
    else if (option === "com_none") {
        jQuery("#alternate-comment-options input").prop("checked", false);
        jQuery(".comgroup input").prop("checked", false);
        jQuery("#options-com-none").prop("checked", true);
    }
    else if (option === "com_int" || option === "com_perm") {
        var internal = jQuery("#options-com-int").prop("checked");
        var permanent = jQuery("#options-com-perm").prop("checked");
        var key = (internal ? "Y" : "N") + (permanent ? "Y" : "N");
        var uncheck = {
            YY: ["aud-ext"],
            YN: ["aud-ext", "dur-perm"],
            NY: ["dur-temp"],
            NN: []
        };
        if (uncheck[key].length) {
            jQuery("#alternate-comment-options input").prop("checked", true);
            uncheck[key].forEach((value) => {
                console.log("unchecking " + value);
                jQuery("#options-com-" + value).prop("checked", false);
            });
            jQuery(".comgroup input").prop("checked", false);
            jQuery("#options-com-int").prop("checked", internal);
            jQuery("#options-com-perm").prop("checked", permanent);
        }
    }
    else if (option === "com_ext" || option === "com_adv") {
        var external = jQuery("#options-com-ext").prop("checked");
        var advisory = jQuery("#options-com-adv").prop("checked");
        var key = (external ? "Y" : "N") + (advisory ? "Y" : "N");
        var uncheck = {
            YY: option === "com_ext" ? ["aud-int", "src-adv"] : ["aud-int"],
            YN: ["aud-int", "src-adv"],
            NY: ["src-ed"],
            NN: []
        };
        if (uncheck[key].length) {
            jQuery("#alternate-comment-options input").prop("checked", true);
            uncheck[key].forEach((value) => {
                console.log("unchecking " + value);
                jQuery("#options-com-" + value).prop("checked", false);
            });
            jQuery(".comgroup input").prop("checked", false);
            jQuery("#options-com-ext").prop("checked", external);
            jQuery("#options-com-adv").prop("checked", advisory);
        }
    }
}
