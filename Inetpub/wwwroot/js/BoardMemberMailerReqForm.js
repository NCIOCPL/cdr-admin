/**
 * Client-side scripting for creating board member correspondence mailers.
 */

// Make it possible to detect when the board selection has changed.
var current_board = 0;

// When the board changes, re-populated the fields for members and letters.
function check_board(whatever) {

    // Has the currently selected board changed?
    let board_id = jQuery("#boards input:checked").val();
    console.log("board_id: " + board_id + ", current_board: " + current_board);
    if (board_id != current_board) {

        // Renew the radio button fields for the available letters.
        current_board = board_id;
        jQuery("#letters div").remove();
        let board = boards[board_id];
        let type = board.type;
        console.log("the type is " + type);
        for (var i = 0; i < letters[type].length; ++i) {
            var letter = letters[type][i];
            var name = letter[0];
            var key = letter[1];
            // let [name, key] = letter; poor IE can't cope
            let button = jQuery('<input type="radio", name="letter">');
            button.attr("class", "usa-radio__input");
            button.attr("value", key);
            button.attr("id", key);
            let label = jQuery("<label>");
            label.attr("class", "usa-radio__label");
            label.attr("for", key);
            label.text(name);
            let div = jQuery("<div>");
            div.attr("class", "usa-radio");
            div.append(button);
            div.append(label);
            jQuery("#letters").append(div);
        }

        // Do the same for the list of board members.
        jQuery("#members div").remove();
        let all_members = [["all", "All board members"]];
        let members = all_members.concat(boards[board_id].members);
        for (var i = 0; i < members.length; ++i) {
            var member = members[i];
            let id = member[0];
            let name = member[1];
            // let [id, name] = member; aargh!
            let key = "member-" + id;
            let checkbox = jQuery('<input type="checkbox", name="member">');
            checkbox.attr("class", "usa-checkbox__input");
            checkbox.attr("value", id);
            checkbox.attr("id", key);
            let label = jQuery("<label>");
            label.attr("class", "usa-checkbox__label");
            label.attr("for", key);
            label.text(name);
            let div = jQuery("<div>");
            div.attr("class", "usa-checkbox");
            div.append(checkbox);
            div.append(label);
            jQuery("#members").append(div);
        }

        // Make sure the new widgets know what to do when they're clicked.
        jQuery("#members input").click(function() { check_member(this); });
        jQuery("#letters input").click(function() { check_submit_button() });
    }
}

// Add some additional logic to the "All board members" checkbox.
function check_member(checkbox) {
    if (checkbox.id == "member-all") {
        if (checkbox.checked) {
            jQuery("#members input").prop("checked", true);
        }
        else
            jQuery("#members input").prop("checked", false);
    }
    else {
        if (!checkbox.checked)
            jQuery("#member-all").prop("checked", false);
    }
    check_submit_button();
}

// Show the submit button only if we have a letter and at least one recipient.
function check_submit_button() {
    let recipients = jQuery("#members input:checked").length;
    let letter = jQuery("#letters input:checked").val();
    console.log("recipients: " + recipients + " letter: " + letter);
    if (!letter || recipients < 1)
        jQuery("#submit-button-submit").hide();
    else
        jQuery("#submit-button-submit").show();
}

// Plug in the handler for changes to the board selection, and run it now.
jQuery(function() {
    jQuery("#boards input").click(function() { check_board(); });
    check_board();
    check_submit_button();
});
