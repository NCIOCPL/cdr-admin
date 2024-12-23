function add_filter_field() {
    var id = jQuery(".filter").length + 1;
    jQuery("#filters").append('<div class="labeled-field filter"> ' +
        //'<label class="usa-label" for="filter-' + id + '">Filter ' + id +
        //'</label> ' +
        '<input name="filter" id="filter-' + id + '" ' +
        'class="usa-input usa-input--xl"> ' +
        '</div>');
}
function add_parameter_fields() {
    var id = jQuery(".parameter").length + 1;
    console.log("add_parameter_fields(): id=" + id);
    jQuery("#parm-count").val(id);
    jQuery("#parameters").append('<div class="parameter"> ' +
        '<div class="labeled-field parm-name">' +
        '<label class="usa-label" for="parm-name-' + id + '">Name</label> ' +
        '<input class="usa-input usa-input--xl" name="parm-name-' + id +
        '" id="parm-name-' + id + '"> ' +
        '</div><div class="labeled-field">' +
        '<label class="usa-label" for="parm-value-' + id +
        '">Value</label> ' +
        '<input class="usa-input usa-input--xl" name="parm-value-' + id +
        '" id="parm-value-' + id + '"> ' +
        '</div></div>');
}
function check_glossary() {
    if (jQuery("#glossary:checked").length == 1) {
        jQuery("#glosspatient").prop("checked", true);
        jQuery("#glosshp").prop("checked", true);
    }
}
