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
                templateUrl: remindListUrl,
                controller: 'RemindListCtrl',
                controllerAs: 'remindListCtrl'
            })
            .state('remind-detail', {
                url: '/:id',
                templateUrl: remindDetailUrl,
                controller: 'RemindDetailCtrl',
                controllerAs: 'remindDetailCtrl'
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
    .factory('wecronHttp', function($http, $ionicLoading, $ionicPopup, $rootScope, indicator, $state, $location) {
        function httpRequest(url, method, onSuccess, payload) {
            method = method || 'get';
            $ionicLoading.show({
                delay: 500,
                templateUrl: 'loading-toast'
            });
            return $http({
                method: method,
                url: url,
                data: payload,
                timeout: 50000,
                headers: {
                    "X-Referer": $location.absUrl()
                }
            }).success(function (resp) {
                onSuccess && onSuccess(resp);
            }).error(function (body, status, header, config) {
                var msg = '请稍候再试~';
                var okText = '好的';
                var title = '哎呀，出错啦！！！';
                if (status == 404) {
                    msg = '没找到这个提醒，你是不是进错地方了？';
                    okText = '关闭';
                } else if (status == 404) {
                    title = '没有权限';
                    msg = '亲，你不能这样做哦';
                    okText = '关闭';
                }
                $ionicPopup.alert({
                    title: title,
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
                    httpRequest('/reminds/api/' + id + '/', 'delete', function () {
                        if (list != undefined) {
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
            });
        };
        return {
            getList: function (onSuccess) {
                httpRequest('/reminds/api/', 'get', onSuccess);
            },
            getObject: function (id, onSuccess) {
                httpRequest('/reminds/api/'+id+'/', 'get', onSuccess);
            },
            update: function (id, payload, onSuccess) {
                httpRequest('/reminds/api/'+id+'/', 'patch', function (resp) {
                    indicator.show('更新成功', 2000);
                    onSuccess && onSuccess(resp);
                }, payload);
            }
        }
    })
    .controller('RemindListCtrl', function($scope, wecronHttp, $filter){
        var ctrl = this;
        ctrl.remindList = [];

        wecronHttp.getList(function(remindList) {
            ctrl.remindList = remindList;
        });

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

    })
    .controller('RemindDetailCtrl', function($scope, $stateParams, wecronHttp, $ionicPopup) {
        var ctrl = this;
        wecronHttp.getObject($stateParams.id, function(remind) {
            remind.time = new Date(remind.time);
            ctrl.modified = false;
            ctrl.model = remind;
        });

        ctrl.update = function () {
            wecronHttp.update($stateParams.id, {
                time: ctrl.model.time.getTime(),
                desc: ctrl.model.desc,
                defer: ctrl.model.defer,
                title: ctrl.model.title
            }, function () {
                ctrl.originModel = angular.copy(ctrl.model);
                ctrl.modified = false;
            });
        };
        ctrl.canEdit = function () {
            return ctrl.model && ctrl.model.owner && ctrl.model.owner.id==userID;
        };
        $scope.$watch(function () {
           return ctrl.model;
        }, function (newVal, oldVal) {
            if(oldVal) {
                ctrl.modified = !angular.equals(ctrl.originModel, ctrl.model);
            } else {
                ctrl.originModel = angular.copy(ctrl.model);
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
                onConfirm: function (result) {
                    ctrl.model.defer = result.reduce(function(a, b){return a*b});
                    console.log(ctrl.model);
                    $scope.$apply();
                },
                id: 'deferPicker'
            });
        };
        ctrl.showRepeatPicker = function () {
            $ionicPopup.alert({
                title: '客官莫急',
                template: '此功能正在开发',
                okText: '好的'
            });
        };
        ctrl.setEdit = function () {
            document.getElementById('remind-title').focus();
        };
    }).directive('natureTimeDefer', function () {
        return {
            require: '^ngModel',
            restrict: 'A',
            link: function (scope, elm, attrs, ctrl) {
                ctrl.$formatters.unshift(function (modelValue) {
                    modelValue = parseInt(modelValue);
                    if (!modelValue) {
                        return '准时';
                    }
                    var natualUnits = [['周', 10080], ['天', 1440], ['小时', 60], ['分钟', 1]];
                    for (var idx in natualUnits) {
                        var unit = natualUnits[idx][0];
                        var minutes = natualUnits[idx][1];
                        if (modelValue % minutes === 0)
                            return (modelValue < 0 ? '提前' : '延后') + Math.abs(modelValue / minutes) + unit;
                    }
                    return (modelValue < 0 ? '提前' : '延后') + Math.abs(modelValue) + '分钟';
                });
            }
        };
    });