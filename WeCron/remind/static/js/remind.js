'use strict';
angular.module('remind', ['ionic'])
    .config(function ($httpProvider, $stateProvider, $ionicConfigProvider, $urlRouterProvider) {
        $httpProvider.defaults.xsrfCookieName = 'csrftoken';
        $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
        $urlRouterProvider.otherwise('/');
        $ionicConfigProvider.templates.maxPrefetch(0);
        $stateProvider
            .state('remind-list', {
                url: '/',
                templateUrl: '/static/tpls/remind_list.html',
                controller: 'RemindListCtrl',
                controllerAs: 'remindListCtrl'
            })
            .state('remind-detail', {
                url: '/:id',
                templateUrl: '/static/tpls/remind_detail.html',
                controller: 'RemindDetailCtrl',
                controllerAs: 'remindDetailCtrl'
            });
    })
    // .constant('$ionicLoadingConfig', {
    //     delay: 1000,
    //     templateUrl: 'loading-toast'
    // })
    .factory('indicator', function($ionicLoading) {
        return {
            toast: function (title) {
                var msg = '<div class="weui-mask_transparent"></div>' +
                    '<div class="weui-toast">' +
                    '<i class="weui-icon-success-no-circle weui-icon_toast"></i>' +
                    '<p class="weui-toast__content">' + title + '</p></div>';
                $ionicLoading.show({
                    template: msg,
                    duration: 3000,
                    noBackdrop: true
                });
            }
        };
    })
    .factory('wecronHttp', function($http, $ionicLoading, $ionicPopup, $rootScope, indicator, $state) {
        function setErrorHandler(promise) {
            promise.error(function (body, status, header, config) {
                var msg = '请稍候再试~';
                var okText = '好的';
                if (status == 404) {
                    msg = '没找到这个提醒，你是不是进错地方了？';
                    okText = '关闭';
                }
                $ionicPopup.alert({
                    title: '哎呀，出错啦！！！',
                    template: msg,
                    okText: okText
                });
            }).finally(function () {
                $ionicLoading.hide();
            });
        }

        $rootScope.deleteRemind = function (id, list) {
            return $ionicPopup.confirm({
                title: '确认删除？',
                cancelText: '不',
                okText: '是的',
                okType: 'button-assertive'
            }).then(function (res) {
                if (res) {
                    $ionicLoading.show({
                        delay: 1000,
                        templateUrl: 'loading-toast'
                    });
                    var promise = $http.delete('/reminds/api/' + id + '/', {
                        timeout: 50000
                    }).success(function () {
                        if(list != undefined) {
                            for(var i=0; i<list.length; ++i) {
                                if(list[i].id===id){
                                    list.splice(i, 1);
                                    break;
                                }
                            }
                        }
                        indicator.toast('删除成功');
                        $state.go('remind-list');
                    });
                    setErrorHandler(promise);
                    return promise;
                }
            });
        };
        return {
            get: function (url) {
                $ionicLoading.show({
                    delay: 1000,
                    templateUrl: 'loading-toast'
                });
                var promise = $http.get(url, {
                    timeout: 50000
                });
                setErrorHandler(promise);
                return promise;
            }
        }
    })
    .controller('RemindListCtrl', function($scope, wecronHttp, $filter){
        var ctrl = this;
        ctrl.remindList = [];

        $scope.$watchCollection(function () {
            return ctrl.remindList;
        }, function (newVal) {
            groupByDate(newVal);
        });

        function groupByDate(remindList){
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

        wecronHttp.get('/reminds/api/').success(function(remindList) {
            ctrl.remindList = remindList;
        });

    })
    .controller('RemindDetailCtrl', function($scope, $stateParams, wecronHttp, $ionicPopup, indicator, $state) {
        var ctrl = this;
        wecronHttp.get('/reminds/api/'+$stateParams.id+'/').success(function(remind){
            remind.time = new Date(remind.time);
            ctrl.modified = false;
            ctrl.model = remind;
        });
        $scope.$watch(function () {
           return ctrl.model;
        }, function (newVal, oldVal) {
            if(oldVal) {
                ctrl.modified = true;
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
                onChange: function (result) {
                    console.log(result)
                },
                onConfirm: function (result) {
                    ctrl.model.defer = result.reduce(function(a, b){return a*b});
                    console.log(ctrl.model);
                    $scope.$apply();
                },
                id: 'deferPicker'
            });
        };
        ctrl.setEdit = function () {
            document.getElementById('remind-title').focus();
        };
        ctrl.update = function () {
            console.log(ctrl.model);
        };
    }).filter('natureTimeDefer', function () {
        return function (defer) {
            if (!defer) {
                return '准时';
            }
            var natualUnits = [['周', 10080], ['天', 1440], ['小时', 60], ['分钟', 1]];
            for (var idx in natualUnits) {
                var unit = natualUnits[idx][0];
                var minutes = natualUnits[idx][1];
                if (defer % minutes === 0)
                    return (defer < 0 ? '提前' : '延后') + Math.abs(defer / minutes) + unit;
            }
            return (defer < 0 ? '提前' : '延后') + Math.abs(defer) + '分钟';
        };
    });