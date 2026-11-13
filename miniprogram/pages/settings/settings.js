const api = require('../../utils/api');
const fmt = require('../../utils/format');
const TIMEZONES = require('../../utils/timezones');

const DEFAULT_TZ = 'Asia/Shanghai';

Page({
  data: {
    profile: null,
    failed: false,
    avatar: '',
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
          hasMorningGreeting: !!profile.morning_greeting,
          notifySubscription: !!profile.notify_subscription,
          timezoneIndex
        };
        this.setData({
          profile,
          notSubscribed: false,
          avatar: fmt.avatar(profile.headimgurl),
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

  // Saves one field. Requests are serialised so the server ends up with the last choice, and a failure only
  // reverts the field when no newer save of it is pending, back to what the server really has
  save(field, value, patch) {
    const seq = ++this.seq;
    this.latest[field] = seq;
    this.setData({ [field]: value });
    this.pending = (this.pending || Promise.resolve())
      .then(() => api.updateProfile(patch))
      .then(() => {
        this.confirmed[field] = value;
        if (this.latest[field] === seq) wx.showToast({ title: '已保存', icon: 'success' });
      })
      .catch(() => {
        if (this.latest[field] === seq) this.setData({ [field]: this.confirmed[field] });
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
