const api = require('./utils/api');

App({
  globalData: {
    user: null,
    // Shown by the detail page before its own request completes
    currentRemind: null,
    // Reminds may have been changed in the detail page, or created in the official account meanwhile
    listDirty: false
  },

  onLaunch() {
    this.globalData.user = api.getUser();
  },

  onShow() {
    this.globalData.listDirty = true;
  },

  userID() {
    const user = this.globalData.user || api.getUser();
    return user ? user.id : null;
  }
});
