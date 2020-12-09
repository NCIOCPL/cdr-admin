function check_method(method) {
    jQuery.each(['name', 'date', 'type', 'fda'], function(i, block) {
        if (block == method)
            jQuery('#' + block + '-block').show();
        else
            jQuery('#' + block + '-block').hide();
    });
}

jQuery(document).ready(function($) {
    $('#drugs option').click(function() {
        switch ($(this).val()) {
        case 'all-drugs':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-drugs"]').prop('selected', true);
            break;
        case 'all-single-agent-drugs':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-single-agent-drugs"]')
                .prop('selected', true);
            break;
        case 'all-drug-combinations':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-drug-combinations"]')
                .prop('selected', true);
            break;
        default:
            $('#drugs option[value="all-drugs"]').prop('selected', false);
            $('#drugs option[value="all-single-agent-drugs"]')
                .prop('selected', false);
            $('#drugs option[value="all-drug-combinations"]')
                .prop('selected', false);
            break;
        }
    });
    check_method($('input[name=method]:checked').val());
});
