var app = new Framework7({
    pushState: true,
    cache: false,
    router: false,
    onAjaxStart: function (xhr) {
        app.showIndicator();
    },
    onAjaxComplete: function (xhr) {
        app.hideIndicator();
    }
});
