$(function () {
    'use strict';

    $.showIndicator = function() {
        $('#loadingToast').show();
    };
    $.hideIndicator = function() {
        $('#loadingToast').hide();
    };

    $(window).on("pageLoadComplete", function() {
      $.hideIndicator();
    });

    $(document).on("pageInit", 'form', function (e) {
        if(!$.device.android) return;
        var $input = $("input[type='datetime-local']");
        var d = $input.val();
        $input.attr('type', 'text');
        $input.val(d.replace('T', ' '));
        $input.datetimePicker({
            toolbarTemplate: '<header class="bar bar-nav">\
                <button class="button button-link pull-right close-picker">确定</button>\
                <h1 class="title">选择时间</h1>\
                </header>',
            //value: [].concat(d.split("T")[0].split("-"), d.split("T")[1].split(":")),
            //formatValue: function (p, values, displayValues) {
            //    return displayValues[0] + '-' + values[1] + '-' + values[2] + 'T' + values[3] + ':' + values[4];
            //}
        });
    });

    $('.swipeout').on('deleted', function (e) {
        $.router.replacePage($('.swipeout-delete', this).data('delete-link'));
    });

    var loadingBefore = false;
    var loadingAfter = false;
    $(document).on('refresh', '.pull-to-refresh-content', function(e) {
        if(!loadingBefore) {
            loadingBefore = true;
            var url = location.href + '?before=1&date=' + $(e.target).find('a.item-link').data('date');
            $.router.getPage(url, function($page, $extra) {
                var list = $('.list-block', $page).children();
                if(list.length) {
                    $('#no-remind').remove();
                }
                $('.list-block').prepend(list);
                loadingBefore = false;
            });
        }
        // done
        $.pullToRefreshDone('.pull-to-refresh-content');
    });

    $.init();
});