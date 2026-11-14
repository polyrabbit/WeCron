const api = require('../../utils/api');
const fmt = require('../../utils/format');
const TIMEZONES = require('../../utils/timezones');

const DEFAULT_TZ = 'Asia/Shanghai';

const app = getApp();

Page({
  data: {
    profile: null,
    failed: false,
    avatar: '',
    nickname: '',
    hasMorningGreeting: false,
    notifySubscription: true,
    timezoneLabels: TIMEZONES.map((t) => t.label),
    timezoneIndex: 0,
    notSubscribed: false
  },

  onLoad() {
    this.load();
  },

  onShow() {
    // A failed first load would otherwise leave the page empty forever
    if (!this.data.profile && !this.loading) this.load();
  },

  load() {
    this.loading = true;
    this.setData({ failed: false });
    return api.getProfile()
      .then((profile) => {
        const tz = profile.timezone || DEFAULT_TZ;
        let timezoneIndex = TIMEZONES.findIndex((t) => t.value === tz);
        if (timezoneIndex < 0) timezoneIndex = TIMEZONES.findIndex((t) => t.value === DEFAULT_TZ);
        this.lastGreetingTime = profile.morning_greeting;
        this.confirmed = {
          nickname: profile.nickname || '',
          hasMorningGreeting: !!profile.morning_greeting,
          notifySubscription: !!profile.notify_subscription,
          timezoneIndex
        };
        this.setData({
          profile,
          notSubscribed: false,
          avatar: fmt.avatar(profile.headimgurl),
          nickname: profile.nickname || '',
          hasMorningGreeting: !!profile.morning_greeting,
          notifySubscription: !!profile.notify_subscription,
          timezoneIndex
        });
      })
      .catch((err) => this.setData({
        notSubscribed: err.code === 'not_subscribed',
        failed: err.code !== 'not_subscribed'
      }))
      .finally(() => {
        this.loading = false;
      });
  },

  lastGreetingTime: null,
  // Per field: the value the server last accepted, and the sequence number of the newest save
  confirmed: {},
  latest: {},
  seq: 0,

  // Saves one field, resolves to whether it succeeded. Requests are serialised so the server ends up with
  // the last choice, and a failure only reverts the field when no newer save of it is pending
  save(field, value, patch) {
    const seq = ++this.seq;
    this.latest[field] = seq;
    this.setData({ [field]: value });
    this.pending = (this.pending || Promise.resolve())
      .then(() => api.updateProfile(patch))
      .then(() => {
        this.confirmed[field] = value;
        if (this.latest[field] === seq) wx.showToast({ title: '已保存', icon: 'success' });
        return true;
      })
      .catch(() => {
        if (this.latest[field] === seq) this.setData({ [field]: this.confirmed[field] });
        return false;
      });
    return this.pending;
  },

  // WeChat reviews the nickname input after blur and clears it if rejected, only what passed is saved.
  // A review result can't tell which value it was for, so any edit while one is pending voids it.
  onNicknameBlur(e) {
    const value = e.detail.value.trim();
    if (this.reviewing !== undefined) this.uncertain = true;
    if (value && value !== this.confirmed.nickname) this.reviewing = value;
  },

  onNicknameInput() {
    if (this.reviewing !== undefined) this.uncertain = true;
  },

  onNicknameReview(e) {
    const value = this.reviewing;
    const uncertain = this.uncertain;
    this.reviewing = undefined;
    this.uncertain = false;
    if (!e.detail.pass || uncertain || value === undefined) {
      this.setData({ nickname: this.confirmed.nickname });
      if (!e.detail.pass) wx.showToast({ title: '昵称未通过审核', icon: 'none' });
      return;
    }
    this.save('nickname', value, { nickname: value }).then((saved) => {
      if (!saved) return;
      // The list shows the nickname on every remind, it may already be on screen
      app.globalData.listDirty = true;
      const page = getCurrentPages().pop();
      if (page.route === 'pages/list/list') page.reload();
    });
  },

  onMorningGreetingChange(e) {
    const on = e.detail.value;
    this.save('hasMorningGreeting', on, { morning_greeting: on ? (this.lastGreetingTime || '08:00') : null });
  },

  onNotifyChange(e) {
    const on = e.detail.value;
    this.save('notifySubscription', on, { notify_subscription: on });
  },

  onTimezoneChange(e) {
    const index = Number(e.detail.value);
    this.save('timezoneIndex', index, { timezone: TIMEZONES[index].value });
  }
});
