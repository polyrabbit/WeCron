const api = require('../../utils/api');
const fmt = require('../../utils/format');

const app = getApp();
const DELETE_BUTTON_RPX = 160;

Page({
  data: {
    groups: [],
    loaded: false,
    failed: false,
    notSubscribed: false,
    hasPrevious: false,
    hasNext: false,
    refreshing: false,
    loadingNext: false
  },

  reminds: [],
  previousUrl: null,
  nextUrl: null,
  swipe: null,
  openKey: null,
  // Bumped on every reload, responses of older requests are dropped
  generation: 0,

  onLoad() {
    this.deleteWidth = wx.getWindowInfo().windowWidth / 750 * DELETE_BUTTON_RPX;
    this.reload();
  },

  onShow() {
    if (app.globalData.listDirty && this.data.loaded) this.reload();
  },

  reload() {
    // The current list stays as it is until the new one arrives, it is what the user sees and taps
    app.globalData.listDirty = false;
    const generation = ++this.generation;
    this.reloading = true;
    return api.getList()
      .then((page) => {
        if (generation !== this.generation) return;
        this.reminds = page.results;
        this.previousUrl = page.previous || null;
        this.nextUrl = page.next || null;
        this.setData({ notSubscribed: false, loaded: true, failed: false });
        this.render();
      })
      .catch((err) => {
        if (generation !== this.generation) return;
        this.setData({
          notSubscribed: err.code === 'not_subscribed',
          // Keep the page retryable, a failed load is not an empty list
          failed: err.code !== 'not_subscribed'
        });
      })
      .finally(() => {
        if (generation === this.generation) this.reloading = false;
      });
  },

  render() {
    const userID = app.userID();
    const reminds = this.reminds.map((r) => Object.assign({}, r, {
      timeText: fmt.formatTime(r.time),
      avatar: fmt.avatar(r.owner.headimgurl),
      repeatText: fmt.getRepeat(r.repeat) ? fmt.formatRepeat(r.repeat) : '',
      isOwner: r.owner.id === userID,
      offset: 0
    }));
    this.openKey = null;
    this.setData({
      groups: fmt.groupByDate(reminds),
      hasPrevious: !!this.previousUrl,
      hasNext: !!this.nextUrl
    });
  },

  retry() {
    this.setData({ failed: false });
    this.reload();
  },

  onPullDownRefresh() {
    const done = () => {
      this.setData({ refreshing: false });
      wx.stopPullDownRefresh();
    };
    if (this.data.notSubscribed || !this.data.loaded || this.data.failed) {
      this.setData({ failed: false });
      this.reload().finally(done);
      return;
    }
    if (this.reloading) {
      done();
      return;
    }
    if (!this.previousUrl) {
      done();
      wx.showToast({ title: '没有更早的提醒了', icon: 'none' });
      return;
    }
    const generation = this.generation;
    this.setData({ refreshing: true });
    api.getList(this.previousUrl)
      .then((page) => {
        if (generation !== this.generation) return;
        this.reminds = page.results.concat(this.reminds);
        this.previousUrl = page.previous || null;
        this.render();
      })
      .catch(() => {
        // Keep the cursor, so pulling down again retries instead of ending the history
      })
      .finally(done);
  },

  onReachBottom() {
    // The cursor belongs to the list being replaced
    if (!this.nextUrl || this.data.loadingNext || this.reloading) return;
    const generation = this.generation;
    this.setData({ loadingNext: true });
    api.getList(this.nextUrl)
      .then((page) => {
        if (generation !== this.generation) return;
        this.reminds = this.reminds.concat(page.results);
        this.nextUrl = page.next || null;
        this.render();
      })
      .catch(() => {
        // Keep the cursor, scrolling down again retries
      })
      .finally(() => this.setData({ loadingNext: false }));
  },

  findRemind(id) {
    return this.reminds.find((r) => r.id === id);
  },

  viewDetail(e) {
    if (this.openKey) {
      this.closeSwipe();
      return;
    }
    const { id } = e.currentTarget.dataset;
    app.globalData.currentRemind = this.findRemind(id);
    wx.navigateTo({ url: '/pages/detail/detail?id=' + id });
  },

  deleteRemind(e) {
    const { id } = e.currentTarget.dataset;
    const remind = this.findRemind(id);
    if (!remind) return;
    api.confirmRemove(id, remind.owner.id === app.userID()).then((removed) => {
      if (!removed) {
        this.closeSwipe();
        return;
      }
      this.reminds = this.reminds.filter((r) => r.id !== id);
      this.render();
      // A list fetched before the deletion would bring it back
      if (this.reloading) this.reload();
    });
  },

  // Swipe left to reveal the delete button
  onTouchStart(e) {
    const { g, i } = e.currentTarget.dataset;
    const touch = e.touches[0];
    const key = g + '-' + i;
    if (this.openKey) this.closeSwipe();
    this.swipe = {
      g, i, key,
      x: touch.clientX,
      y: touch.clientY,
      base: this.data.groups[g].reminds[i].offset,
      offset: null,
      horizontal: null
    };
  },

  onTouchMove(e) {
    const s = this.swipe;
    if (!s) return;
    const touch = e.touches[0];
    const dx = touch.clientX - s.x;
    const dy = touch.clientY - s.y;
    if (s.horizontal === null) {
      if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
      s.horizontal = Math.abs(dx) > Math.abs(dy);
    }
    if (!s.horizontal) return;
    const offset = Math.max(-this.deleteWidth, Math.min(0, s.base + dx));
    if (offset !== s.offset) {
      s.offset = offset;
      this.setData({ ['groups[' + s.g + '].reminds[' + s.i + '].offset']: offset });
    }
  },

  onTouchEnd() {
    const s = this.swipe;
    this.swipe = null;
    if (!s || !s.horizontal || s.offset === null) return;
    const open = s.offset < -this.deleteWidth / 3;
    this.setData({ ['groups[' + s.g + '].reminds[' + s.i + '].offset']: open ? -this.deleteWidth : 0 });
    this.openKey = open ? s.key : null;
  },

  closeSwipe() {
    if (!this.openKey) return;
    const [g, i] = this.openKey.split('-');
    this.openKey = null;
    if (this.data.groups[g] && this.data.groups[g].reminds[i]) {
      this.setData({ ['groups[' + g + '].reminds[' + i + '].offset']: 0 });
    }
  },

  onPageScroll() {
    if (this.openKey && !this.swipe) this.closeSwipe();
  }
});
