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
    .factory('remindManager', function($http, $ionicLoading, $rootScope, indicator, $state, $location) {
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
                if(status == 401) {
                    document.title = '微信登录中...';
                    if(headerGetter('WWW-Authenticate')) {
                        location.href = headerGetter('WWW-Authenticate');
                        return;
                    }
                } else if (status == 404) {
                    msg = '没找到这个提醒，你是不是进错地方了？';
                } else if (status == 404) {
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
                }]
            });
        };

        return {
            getList: function (url, onSuccess) {
                url = url || '/reminds/api/';
                return httpRequest(url, 'get', onSuccess);
            },
            get: function (id, onSuccess) {
                return httpRequest('/reminds/api/'+id+'/', 'get', onSuccess);
            },
            update: function (id, payload, onSuccess) {
                return httpRequest('/reminds/api/'+id+'/', 'patch', function (resp) {
                    indicator.show('更新成功', 2000);
                    onSuccess && onSuccess(resp);
                }, payload);
            }
        }
    })
    .controller('RemindListCtrl', function($scope, remindManager, $filter){
        var ctrl = this;
        ctrl.remindList = [];

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
    .controller('RemindDetailCtrl', function($scope, $stateParams, remindManager, $ionicPopup) {
        var ctrl = this;
        remindManager.get($stateParams.id, function(remind) {
            remind.time = new Date(remind.time);
            ctrl.modified = false;
            ctrl.model = remind;
        });

        ctrl.update = function () {
            remindManager.update($stateParams.id, {
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
                    var repeat = ctrl.model.repeat || [0, 0, 0, 0];
                    for(var i=0; i<repeat.length; ++i) {
                        if(repeat[i] != 0) {
                            return [0, repeat[i], i];
                        }
                    }
                    return [0, 0, 0];
                })(),
                onConfirm: function (result) {
                    ctrl.model.repeat = [0, 0, 0, 0];
                    ctrl.model.repeat[result[2]] = result[1];
                    $scope.$apply();
                },
                id: 'repeatPicker'+ctrl.model.id
            });
        };
        ctrl.promptShare = function () {
            $ionicPopup.alert({
                title: '客官莫急',
                template: '此功能正在开发',
                okText: '好的'
            });
        };
        // ctrl.setEdit = function () {
        //     // For iOS
        //     document.getElementById('remind-title').focus();
        //     // For Android
        //     setTimeout(function () {
        //         document.getElementById('remind-title').focus();
        //     }, 0);
        // };
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
                    var repeat = modelValue || [0, 0, 0, 0];
                    for(var i=0; i<repeat.length; ++i) {
                        if(repeat[i] != 0) {
                            return '每'+repeat[i]+(['年', '月', '天', '周'][i]);
                        }
                    }
                    return '不重复';
                });
            }
        };
    });

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