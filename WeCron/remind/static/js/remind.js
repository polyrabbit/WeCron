var app = new Framework7({
    dynamicNavbar: true,
    pushState: true,
    animateNavBackIcon: true,
    //cache: false,
    onAjaxStart: function (xhr) {
        Dom7('#loadingToast').show();
    },
    onAjaxComplete: function (xhr) {
        Dom7('#loadingToast').hide();
    },
    onAjaxError: function (xhr) {
        Dom7('#loadingToast').hide();
    }
});
var mainView = app.addView('.view-main');
