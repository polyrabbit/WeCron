'use strict';
angular.module('eosram', ['ionic'])
  .config(function ($httpProvider, $interpolateProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
  })
  .factory('indicator', function($rootScope, $timeout) {
        return {
            show: function (msg, timeout) {
                $rootScope.message = msg;
                $timeout(function () {
                    $rootScope.message = null;
                }, timeout)
            }
        };
    })
  .controller('RamRemindCtrl', function($scope, $ionicLoading, $http, $location, indicator, $ionicPopup, $ionicActionSheet) {

    function httpRequest(url, method, onSuccess, payload) {
        method = method || 'get';
        $ionicLoading.show({
            delay: 500,
            templateUrl: 'loading-toast'
        });
        var promise = $http({
            method: method,
            url: url,
            data: payload,
            timeout: 50000,
            headers: {
                // Pass current url back, so authentication knows where to redirect to after login successfully
                "X-Referer": $location.absUrl()
            }
        });
        promise.success(function (resp) {
            onSuccess && onSuccess(resp);
        }).error(function (body, status, headerGetter, config) {
            var msg = '请稍候再试~';
            var title = '哎呀，出错啦！！！';
            if(status === 401) {
                document.title = '微信登录中...';
                if(headerGetter('WWW-Authenticate')) {
                    location.href = headerGetter('WWW-Authenticate');
                    return;
                }
            } else if (status === 404) {
                title = '没找到这个提醒';
                msg = '它是不是被删了，或者你进错了地方？';
            } else if (status === 403) {
                title = '没有权限';
                msg = '亲，你不能这样做哦';
            }
            weui.alert(msg, {
                title: title,
                buttons: [{
                    label: '知道了'
                }]
            });
        }).finally(function () {
            $ionicLoading.hide();
        });
        return promise;
    }

    $scope.remind = {threshold: [{increase: true}, {increase: false}],
      percent: [{increase: true, period: 60}, {increase: false, period: 60}]};
    var lastUpdate = angular.copy($scope.remind);

    function updateRemind(newVal) {
      if ((newVal.threshold && newVal.threshold.length)
          || (newVal.percent && newVal.percent.length)) {
        $scope.remind = newVal;
        lastUpdate = angular.copy($scope.remind);
      }
    }

    httpRequest('/eosram/api/', 'get').then(function (resp) {
      updateRemind(resp.data);
    });

    $scope.updateAlert = function () {
      if (!subscribed) {
        $ionicPopup.alert({
          title: '请先订阅公众号“微定时” (价格通知是通过该公众号下发的)',
          template: '<div class="text-center">' +
          '<img class="qrcode" src="http://wx3.sinaimg.cn/small/ac472348gy1fteiuafibmj20by0bywfa.jpg" />' +
          '</div>'
        });
        // return;
      }
      if (angular.equals(lastUpdate, $scope.remind)) {
        return;
      }
      lastUpdate = angular.copy($scope.remind);
      httpRequest('/eosram/api/', 'patch', null, $scope.remind).then(function (resp) {
        updateRemind(resp.data);
        indicator.show(resp.data.errMsg || '更新成功', 2000);
      });
    };

    $scope.formatRemindText = function(remind) {
      if (remind.text) {
        return remind.text;
      }
      var human_period;
      if (remind.period % 60 === 0) {
        human_period = (remind.period / 60 === 1 ? '' : remind.period / 60) + '小时';
      } else {
        human_period = remind.period + '分钟';
      }
      return '每' + human_period + (remind.increase ? '上涨 (%)' : '下跌 (%)');
    };

    $scope.addAnotherRemind = function() {
      // Show the action sheet
      $ionicActionSheet.show({
        buttons: [
          { text: '上涨到 (EOS/KB)', increase: true, type: 'threshold' },
          { text: '下跌到 (EOS/KB)', increase: false, type: 'threshold' },
          { text: '每10分钟上涨 (%)', increase: true, type: 'percent', period: 10 },
          { text: '每10分钟下跌 (%)', increase: false, type: 'percent', period: 10 },
          { text: '每30分钟上涨 (%)', increase: true, type: 'percent', period: 30},
          { text: '每30分钟下跌 (%)', increase: false, type: 'percent', period: 30 },
          { text: '每小时上涨 (%)', increase: true, type: 'percent', period: 60 },
          { text: '每小时下跌 (%)', increase: false, type: 'percent', period: 60 },
        ],
        titleText: '再增加一条提醒项',
        cancelText: '取消',
        cancel: function() {
         // add cancel code..
        },
        buttonClicked: function(index, item) {
          $scope.remind[item.type].push(item);
          return true;
        }
      });
    };

    $scope.showMyQrCode = function () {
      $ionicPopup.alert({
          title: '扫码加我微信，欢迎提供建议及反馈',
          template: '<div class="text-center">' +
          '<img class="qrcode" src="http://wx1.sinaimg.cn/thumb150/ac472348ly1ftbw0wzpjzj20e80e8glx.jpg" />' +
          '</div>'
      });
    };

    $scope.showRechargeDialog = function() {
      $ionicPopup.alert({
          title: 'EOS充值信息',
          template: '' +
            '<div class="list recharge-dialog">\n' +
          '  <label class="item item-input">\n' +
          '    <span class="input-label">充值地址</span>\n' +
          '    <input type="text" readonly value="' + eosAccount + '">\n' +
          '  </label>\n' +
          '  <label class="item item-input">\n' +
          '    <span class="input-label">备注(memo)</span>\n' +
          '    <input type="text" readonly value="' + eosMemo + '">\n' +
          '  </label>\n' +
          '</div>' +
          '<ul class="ram-note"><li>目前价格：1EOS=500次提醒（即10次提醒只需充值0.02EOS）。</li>' +
          '<li>为什么收费：少量的费用一方面可以让这个项目持续下去，另一方面也可以减少一些滥用。</li></ul>'
      });
    };

    $scope.availableQuota = availableQuota;

    var shareCfg = {
            title: '微信中的EOS Ram价格提醒',
            desc: '盯盘伤身，要巧用工具！',
            link: $location.absUrl(),
            imgUrl: userAvatar
        };
    wx.ready(function() {
        wx.onMenuShareAppMessage(shareCfg);
        wx.onMenuShareQQ(shareCfg);
        wx.onMenuShareWeibo(shareCfg);
        wx.onMenuShareQZone(shareCfg);
        // 分享到朋友圈没有desc字段，取title
        wx.onMenuShareTimeline(shareCfg);
    });
  });