var myApp = new Framework7({
    pushState: true,
    cache: false,
    router: false,
    onAjaxStart: function (xhr) {
        myApp.showIndicator();
    },
    onAjaxComplete: function (xhr) {
        myApp.hideIndicator();
    }
});
