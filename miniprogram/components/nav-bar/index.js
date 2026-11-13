// Custom navigation bar, the system one can't have a bigger title
Component({
  properties: {
    title: String,
    // Show a back button, the page handles the tap
    back: Boolean
  },

  data: {
    statusBarHeight: 20,
    navHeight: 44
  },

  lifetimes: {
    attached() {
      const windowInfo = wx.getWindowInfo();
      const statusBarHeight = windowInfo.statusBarHeight || 20;
      // Align the bar with the capsule button of the system
      let navHeight = 44;
      try {
        const capsule = wx.getMenuButtonBoundingClientRect();
        if (capsule && capsule.height) {
          navHeight = (capsule.top - statusBarHeight) * 2 + capsule.height;
        }
      } catch (e) {
        // Older versions without the capsule API
      }
      this.setData({ statusBarHeight, navHeight });
    }
  },

  methods: {
    onBack() {
      this.triggerEvent('back');
    }
  }
});
