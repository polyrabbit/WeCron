$(function () {
    'use strict';

    $.modal.prototype.defaults.modalButtonOk = '确认';
    $.modal.prototype.defaults.modalButtonCancel = '取消';

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

    $(document).on('deleted', '.swipeout', function (e) {
        $.get($('.swipeout-delete', this).data('delete-link'));
    });

    $(document).on("click", ".delete-remind", function(e) {
        var $self = $(this);
        $.confirm("", "确认删除?", function(){
            $.router.loadPage($self.data('delete-link'));
        });
        return false;
    });

    $(document).on('focus change', '.remind-update input, .remind-update textarea', function (e) {
        $('#icon-submit').removeClass('icon-edit').addClass('icon-check');
    });

    var minutes = {'周': 7*24*60, '天': 60*24, '小时': 60, '分钟': 1};

    $(document).on('submit', '.remind-update', function(e) {
        if($('#icon-submit').hasClass('icon-edit')) {
            $('.page-current input').eq(1).focus();
            return false;
        }
        // Set human readable time back to time delta
        //var time_human = $("input.deferred-time-picker").val();
        //for(var unit in minutes) {
        //    if (unit == time_human.split(' ')[1]) {
        //        $("input.deferred-time-picker").val(time_human[0]*minutes[unit]);
        //        break;
        //    }
        //}
    });


    $(document).on("pageInit", 'form', function (e) {
        $("input.deferred-time-picker").picker({
            toolbarTemplate: '<header class="bar bar-nav">\
            <button class="button button-link pull-right close-picker">确定</button>\
            <h1 class="title">设置提醒时间</h1>\
            </header>',
            //updateValuesOnTouchmove: false,
            value: (function () {
                function nomalize(defer) {
                    if (defer === 0) {
                        return ['准时'];
                    }
                    for (var k in minutes) {
                        if (minutes.hasOwnProperty(k)) {
                            var v = minutes[k];
                            if (defer % v === 0) {
                                return [defer<0?'提前':'延后', Math.abs(defer / v), k];
                            }
                        }
                    }
                }
                var defer = parseInt($("input.deferred-time-picker").val());
                $("input.deferred-time-picker").val(nomalize(defer).join(' '));
                return nomalize(defer);
            })(),
            formatValue: function(p, value, displayValue) {
                if(value[1] == '0') {
                    return '准时';
                }
                return value.join(' ');
            },
            cols: [
                {
                    textAlign: 'center',
                    values: ['提前', '延后']
                },
                {
                    textAlign: 'center',
                    values: Array.apply(null, {length: 61}).map(function (element, index) {
                        return index;
                    }),
                },
                {
                    textAlign: 'center',
                    values: ['分钟', '小时', '天', '周']
                }
            ]
        });
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