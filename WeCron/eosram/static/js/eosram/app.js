'use strict';
angular.module('eosram', ['ionic'])
  .config(function ($httpProvider, $stateProvider, $ionicConfigProvider, $urlRouterProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
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
  .controller('RamRemindCtrl', function($scope, $ionicLoading, $http, $location, indicator, $ionicPopup) {

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

    var lastUpdate;
    httpRequest('/eosram/api/', 'get').then(function (resp) {
      $scope.remind = resp.data;
      lastUpdate = angular.copy($scope.remind);
    });
    
    $scope.updateAlert = function () {
      if (!$scope.remind) {
        return;
      }
      if (!subscribed) {
        $ionicPopup.alert({
          title: '请先订阅公众号“微定时” (价格通知是通过该公众号下发的)',
          template: '<div class="text-center">' +
          '<img class="qrcode" src="https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=gQE18TwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyd1BkbWRXMTE5Ul8xMDAwMDAwN2QAAgQNtUxbAwQAAAAA" />' +
          '</div>'
        });
        // return;
      }
      if (angular.equals(lastUpdate, $scope.remind)) {
        return;
      }
      lastUpdate = angular.copy($scope.remind);
      httpRequest('/eosram/api/', 'patch', null, $scope.remind).then(function (resp) {
        indicator.show('更新成功', 2000);
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

    var shareCfg = {
            title: '微信中的EOS Ram价格提醒',
            desc: '盯盘伤身，要巧用工具！',
            link: $location.absUrl() + '?from1=notification',
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