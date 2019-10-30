/**
 * Client-side scripting for creating board member correspondence mailers.
 */

// Make it possible to detect when the board selection has changed.
var current_board = 0;

// When the board changes, re-populated the fields for members and letters.
function check_board() {

    // Has the currently selected board changed?
    let board_id = jQuery("#boards input:checked").val();
    console.log("board_id: " + board_id + ", current_board: " + current_board);
    if (board_id != current_board) {

        // Renew the radio button fields for the available letters.
        jQuery("#letters div").remove();
        let board = boards[board_id];
        let type = board.type;
        console.log("the type is " + type)
        for (const letter of letters[type]) {
            let [name, key] = letter;
            let button = jQuery('<input type="radio", name="letter">');
            button.attr("value", key);
            button.attr("id", key);
            let label = jQuery("<label>");
            label.attr("for", key);
            label.text(name);
            let div = jQuery("<div>");
            div.append(button);
            div.append(label);
            jQuery("#letters").append(div);
        }

        // Do the same for the list of board members.
        jQuery("#members div").remove();
        let all_members = [["all", "All board members"]];
        let members = all_members.concat(boards[board_id].members);
        for (const member of members) { //boards[board_id].members) {
            let [id, name] = member;
            let key = "member-" + id;
            let checkbox = jQuery('<input type="checkbox", name="member">');
            checkbox.attr("value", id);
            checkbox.attr("id", key);
            let label = jQuery("<label>");
            label.attr("for", key);
            label.text(name);
            let div = jQuery("<div>");
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
        jQuery("#submit-button").hide();
    else
        jQuery("#submit-button").show();
}

// Plug in the handler for changes to the board selection, and run it now.
jQuery(function() {
    jQuery("#board input").click(function() { check_board(); });
    check_board();
    let submit = jQuery("#header-buttons input[value='Submit']");
    submit.attr("id", "submit-button");
    check_submit_button();
});
