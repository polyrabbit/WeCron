$(function () {
    'use strict';

    $.showIndicator = function() {
        $('#loadingToast').show();
    };
    $.hideIndicator = function() {
        $('#loadingToast').hide();
    };

    $('.swipeout').on('deleted', function (e) {
        $.router.replacePage($('.swipeout-delete', this).data('delete-link'));
    });

    $.init();
});