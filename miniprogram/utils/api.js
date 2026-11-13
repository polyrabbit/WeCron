const { baseUrl } = require('../config');

const TOKEN_KEY = 'wecron_token';
const USER_KEY = 'wecron_user';

let loginPromise = null;
let loadingCount = 0;
let loadingTimer = null;

class ApiError extends Error {
  constructor(statusCode, data) {
    super((data && data.detail) || ('HTTP ' + statusCode));
    this.statusCode = statusCode;
    this.data = data || {};
    this.code = this.data.code;
  }
}

function getToken() {
  return wx.getStorageSync(TOKEN_KEY);
}

function getUser() {
  return wx.getStorageSync(USER_KEY) || null;
}

function clearLogin() {
  wx.removeStorageSync(TOKEN_KEY);
}

function absUrl(url) {
  return /^https?:\/\//.test(url) ? url : baseUrl + url;
}

// Only show the loading toast for requests longer than 500ms
function showLoading() {
  loadingCount += 1;
  if (loadingCount === 1) {
    loadingTimer = setTimeout(() => {
      wx.showLoading({ title: '数据加载中', mask: true });
      loadingTimer = 'shown';
    }, 500);
  }
}

function hideLoading() {
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount === 0) {
    if (loadingTimer === 'shown') {
      wx.hideLoading();
    } else {
      clearTimeout(loadingTimer);
    }
    loadingTimer = null;
  }
}

function rawRequest({ url, method = 'GET', data, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: absUrl(url),
      method,
      data,
      header: Object.assign({ 'Content-Type': 'application/json' }, header),
      timeout: 50000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new ApiError(res.statusCode, res.data));
        }
      },
      fail(err) {
        reject(new ApiError(0, { detail: err.errMsg }));
      }
    });
  });
}

function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => (res.code ? resolve(res.code) : reject(new ApiError(0, { detail: res.errMsg }))),
      fail: (err) => reject(new ApiError(0, { detail: err.errMsg }))
    });
  });
}

// Concurrent callers share the same login
function login() {
  if (!loginPromise) {
    loginPromise = wxLogin()
      .then((code) => rawRequest({ url: '/miniprogram/login', method: 'POST', data: { code } }))
      .then((resp) => {
        wx.setStorageSync(TOKEN_KEY, resp.token);
        wx.setStorageSync(USER_KEY, resp.user);
        getApp().globalData.user = resp.user;
        return resp;
      })
      .catch((err) => {
        // Errors without a meaning of their own, e.g. a 404 here is not a missing remind
        if (!err.code) err.code = 'login_failed';
        throw err;
      })
      .finally(() => {
        loginPromise = null;
      });
  }
  return loginPromise;
}

function ensureLogin() {
  return getToken() ? Promise.resolve() : login();
}

function showError(err) {
  let title = '哎呀，出错啦！！！';
  let content = '请稍候再试~';
  if (err.statusCode === 0) {
    // wx.request failed before reaching the server, its errMsg tells why, e.g. "url not in domain list"
    title = '网络请求失败';
    content = err.message;
  } else if (err.code === 'login_failed') {
    title = '登录失败';
    content = '请稍后再试（' + err.message + '）';
  } else if (err.code === 'not_subscribed') {
    title = '需要先关注公众号';
    content = '请关注公众号「微定时」后再试';
  } else if (err.code === 'not_configured') {
    title = '服务暂不可用';
    content = '小程序登录尚未配置，请稍后再试';
  } else if (err.statusCode === 404) {
    title = '没找到这个提醒';
    content = '它是不是被删了，或者你进错了地方？';
  } else if (err.statusCode === 403) {
    title = '没有权限';
    content = '亲，你不能这样做哦';
  } else if (err.statusCode === 400 && err.data) {
    // DRF validation errors
    const messages = [].concat(...Object.values(err.data).map((v) => [].concat(v)));
    if (messages.length) content = messages.join('\n');
  }
  wx.showModal({ title, content, showCancel: false, confirmText: '知道了' });
}

// Logs in on demand and retries once if the token is rejected.
// options.silent: no loading toast or error alert
function request(options) {
  const { silent } = options;
  if (!silent) showLoading();
  // Remember the token used, so a late 401 of an old token can't clear a fresh one
  let usedToken = null;
  const send = () => {
    usedToken = getToken();
    return rawRequest(Object.assign({}, options, {
      header: Object.assign({ Authorization: 'Token ' + usedToken }, options.header)
    }));
  };
  return ensureLogin()
    .then(send)
    .catch((err) => {
      // Only a rejected token is worth a retry, replaying a write after any other error can duplicate it
      if (err.statusCode !== 401) throw err;
      if (usedToken && usedToken === getToken()) clearLogin();
      // Every request rejected at the same time waits for the same login
      return ensureLogin().then(send);
    })
    .catch((err) => {
      console.error('[api]', options.method || 'GET', options.url, err.statusCode, err.message);
      if (!silent) showError(err);
      throw err;
    })
    .finally(() => {
      if (!silent) hideLoading();
    });
}

// Deletes one's own remind or quits a subscribed one after confirming, resolves to whether it is done
function confirmRemove(id, isOwner) {
  return new Promise((resolve) => wx.showModal({
    title: isOwner ? '确认删除？' : '确认退出？',
    content: isOwner ? '' : '退出后将不再收到这条提醒',
    confirmColor: '#387ef5',
    success: (res) => resolve(res.confirm),
    fail: () => resolve(false)
  })).then((confirmed) => confirmed && request({ url: '/reminds/api/' + id + '/', method: 'DELETE' }).then(() => {
    wx.showToast({ title: isOwner ? '删除成功' : '已退出' });
    return true;
  }));
}

module.exports = {
  getUser,
  confirmRemove,
  getList: (url) => request({ url: url || '/reminds/api/' }),
  get: (id, options) => request(Object.assign({ url: '/reminds/api/' + id + '/' }, options)),
  update: (id, payload) => request({ url: '/reminds/api/' + id + '/', method: 'PATCH', data: payload }),
  subscribe: (id) => request({ url: '/reminds/api/' + id + '/subscribe/', method: 'POST' }),
  getProfile: () => request({ url: '/profile/api/' }),
  updateProfile: (payload) => request({ url: '/profile/api/', method: 'PATCH', data: payload })
};
