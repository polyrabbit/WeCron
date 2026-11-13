const api = require('../../utils/api');
const fmt = require('../../utils/format');

const app = getApp();

const DEFER_DIRECTIONS = [{ label: '提前', value: -1 }, { label: '延后', value: 1 }];
const REPEAT_NAMES = fmt.REPEAT_NAMES;
// Units the backend can schedule, Remind.reschedule() ignores minutes
const REPEAT_UNITS = ['year', 'month', 'day', 'week', 'hour'];

// Keeps an existing unsupported unit selectable, so confirming the picker doesn't change it
function repeatUnitsWith(key) {
  return key && REPEAT_UNITS.indexOf(key) === -1 ? REPEAT_UNITS.concat([key]) : REPEAT_UNITS;
}
const EDITABLE_FIELDS = ['title', 'time', 'defer', 'repeat', 'desc'];

// Counts 0..99
const COUNTS = Array.from({ length: 100 }, (_, i) => i);

// Adds the current value to the choices, so confirming a picker never silently changes it
function countsWith(value) {
  return COUNTS.indexOf(value) === -1 ? COUNTS.concat([value]).sort((a, b) => a - b) : COUNTS;
}

function pick(remind) {
  const r = {};
  EDITABLE_FIELDS.forEach((k) => { r[k] = remind[k]; });
  r.repeat = Object.assign({}, remind.repeat);
  r.desc = remind.desc || '';
  return r;
}

Page({
  data: {
    id: '',
    model: null,
    view: {},
    canEdit: false,
    isOwner: false,
    modified: false,
    notSubscribed: false,
    notFound: false,
    loadFailed: false,
    showParticipants: false,
    people: [],
    // Ranges are rebuilt from the current value on every render, see refreshView()
    deferRange: [DEFER_DIRECTIONS.map((d) => d.label), COUNTS.map(String), fmt.DEFER_UNITS.map((u) => u.label)],
    deferIndex: [0, 0, 0],
    repeatRange: [['每'], COUNTS.map(String), REPEAT_UNITS.map((k) => REPEAT_NAMES[k])],
    repeatIndex: [0, 0, 0]
  },

  remind: null,
  original: null,

  onLoad(options) {
    this.setData({ id: options.id });
    const cached = app.globalData.currentRemind;
    if (cached && cached.id === options.id) {
      this.setRemind(cached);
    }
    this.load();
  },

  load() {
    const silent = !!this.data.model;
    const seq = this.loadSeq = (this.loadSeq || 0) + 1;
    return api.get(this.data.id, { silent })
      .then((remind) => {
        // A save or a newer load happened meanwhile
        if (seq !== this.loadSeq) return;
        this.setData({ notSubscribed: false, notFound: false, loadFailed: false });
        // The cached remind is editable straight away, never throw away what was typed meanwhile
        if (!this.data.modified) this.setRemind(remind);
        this.askToSubscribe(remind);
      })
      .catch((err) => {
        this.setData({
          notSubscribed: err.code === 'not_subscribed',
          notFound: err.statusCode === 404,
          loadFailed: !this.data.model && err.code !== 'not_subscribed' && err.statusCode !== 404
        });
      });
  },

  setRemind(remind) {
    const userID = app.userID();
    const isOwner = remind.owner.id === userID;
    this.remind = remind;
    this.original = pick(remind);
    this.setData({
      model: pick(remind),
      isOwner,
      canEdit: isOwner,
      modified: false,
      people: [remind.owner].concat(remind.participants || []).map((p) => ({
        id: p.id,
        nickname: p.nickname || '微信用户',
        avatar: fmt.avatar(p.headimgurl)
      }))
    });
    this.refreshView();
  },

  refreshView() {
    const m = this.data.model;
    const defer = m.defer || 0;
    const unit = fmt.deferUnit(defer);
    const deferCount = unit ? Math.abs(defer / unit.value) : 0;
    const deferCounts = countsWith(deferCount);
    const deferIndex = unit
      ? [defer > 0 ? 1 : 0, deferCounts.indexOf(deferCount), fmt.DEFER_UNITS.indexOf(unit)]
      : [0, 0, 0];
    const repeat = fmt.getRepeat(m.repeat);
    const repeatCounts = countsWith(repeat ? repeat.count : 0);
    this.repeatUnits = repeatUnitsWith(repeat && repeat.key);
    const repeatIndex = repeat
      ? [0, repeatCounts.indexOf(repeat.count), this.repeatUnits.indexOf(repeat.key)]
      : [0, 0, 0];
    this.setData({
      view: {
        date: fmt.formatDate(m.time),
        time: fmt.formatTime(m.time),
        dateText: fmt.groupTitle(m.time),
        defer: fmt.formatDefer(defer),
        repeat: fmt.formatRepeat(m.repeat)
      },
      deferRange: [
        DEFER_DIRECTIONS.map((d) => d.label),
        deferCounts.map(String),
        fmt.DEFER_UNITS.map((u) => u.label)
      ],
      deferIndex,
      repeatRange: [['每'], repeatCounts.map(String), this.repeatUnits.map((k) => REPEAT_NAMES[k])],
      repeatIndex,
      modified: this.isModified()
    });
  },

  // Fields edited since loaded, only these are saved so that newer server values of the others are kept
  changes() {
    const m = this.data.model;
    const changes = {};
    EDITABLE_FIELDS.forEach((k) => {
      if (JSON.stringify(m[k]) !== JSON.stringify(this.original[k])) changes[k] = m[k];
    });
    return changes;
  },

  isModified() {
    return Object.keys(this.changes()).length > 0;
  },

  askToSubscribe(remind) {
    const userID = app.userID();
    const ids = (remind.participants || []).map((p) => p.id).concat(remind.owner.id);
    if (!userID || ids.indexOf(userID) !== -1) return;
    wx.showModal({
      title: '是否订阅此提醒？',
      content: remind.title + (remind.desc ? '\n' + remind.desc : ''),
      confirmText: '订阅',
      confirmColor: '#387ef5',
      success: (res) => {
        if (!res.confirm) return;
        api.subscribe(remind.id)
          .then((newRemind) => {
            this.setRemind(newRemind);
            app.globalData.listDirty = true;
            wx.showToast({ title: '订阅成功' });
          });
      }
    });
  },

  // Typing only changes whether there is something to save, the pickers stay as they are
  onTextInput(e) {
    this.setData({ ['model.' + e.currentTarget.dataset.field]: e.detail.value });
    this.setData({ modified: this.isModified() });
  },

  onDateChange(e) {
    const [y, mo, d] = e.detail.value.split('-').map(Number);
    const t = new Date(this.data.model.time);
    t.setFullYear(y, mo - 1, d);
    this.setData({ 'model.time': t.getTime() });
    this.refreshView();
  },

  onTimeChange(e) {
    const [h, mi] = e.detail.value.split(':').map(Number);
    const t = new Date(this.data.model.time);
    t.setHours(h, mi, 0, 0);
    this.setData({ 'model.time': t.getTime() });
    this.refreshView();
  },

  onDeferChange(e) {
    const [dir, count, unit] = e.detail.value;
    const defer = DEFER_DIRECTIONS[dir].value * Number(this.data.deferRange[1][count]) * fmt.DEFER_UNITS[unit].value;
    this.setData({ 'model.defer': defer });
    this.refreshView();
  },

  onRepeatChange(e) {
    const [, count, unit] = e.detail.value;
    const value = Number(this.data.repeatRange[1][count]);
    const key = this.repeatUnits[unit];
    const old = this.data.model.repeat || {};
    // Nothing but the interval, a leftover "original_day" alone would still count as repeating on the backend
    const repeat = {};
    if (value) {
      repeat[key] = value;
      if (key === 'month' && old.month && old.original_day) repeat.original_day = old.original_day;
    }
    this.setData({ 'model.repeat': repeat });
    this.refreshView();
  },

  save() {
    // Saving marks it as not sent, an unchanged one-off remind could be sent again
    if (this.saving || !this.data.modified) return;
    const m = this.data.model;
    if (!m.title.trim()) {
      wx.showToast({ title: '请输入提醒内容', icon: 'none' });
      return;
    }
    this.saving = true;
    // Outdates loads still in flight
    this.loadSeq = (this.loadSeq || 0) + 1;
    const submitted = pick(m);
    api.update(this.data.id, this.changes()).then((remind) => {
      app.globalData.listDirty = true;
      // Keeps what was typed while saving, everything else is what the server has now, e.g. a cleared original_day
      const draft = this.data.model;
      const patch = {};
      EDITABLE_FIELDS.forEach((k) => {
        if (JSON.stringify(draft[k]) !== JSON.stringify(submitted[k])) patch['model.' + k] = draft[k];
      });
      this.setRemind(remind);
      if (Object.keys(patch).length) {
        this.setData(patch);
        this.refreshView();
      }
      wx.showToast({ title: '更新成功' });
    }).finally(() => {
      this.saving = false;
    });
  },

  remove() {
    api.confirmRemove(this.data.id, this.data.isOwner).then((removed) => {
      if (!removed) return;
      app.globalData.listDirty = true;
      setTimeout(() => this.goHome(), 800);
    });
  },

  goHome() {
    if (getCurrentPages().length > 1) {
      wx.navigateBack();
    } else {
      wx.switchTab({ url: '/pages/list/list' });
    }
  },

  openParticipants() {
    if (this.data.people.length <= 1) {
      wx.showModal({
        title: '参与者',
        content: '目前还没有人订阅这条提醒，快点击下方“分享”，把它发给好友或群聊，让别的小伙伴也能收到这个提醒吧~',
        showCancel: false,
        confirmText: '好的'
      });
      return;
    }
    this.setData({ showParticipants: true });
  },

  closeParticipants() {
    this.setData({ showParticipants: false });
  },

  noop() {},

  onShareAppMessage() {
    const remind = this.remind;
    if (!remind) return {};
    return {
      title: '[微定时] ' + remind.title + ' ' + fmt.formatDate(remind.time) + ' ' + fmt.formatTime(remind.time),
      path: '/pages/detail/detail?id=' + remind.id
    };
  }
});
