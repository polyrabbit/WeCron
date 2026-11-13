const { adUnits } = require('../../config');

Component({
  properties: {
    // Key of adUnits in config.js
    position: String
  },

  data: {
    unitId: '',
    hidden: false
  },

  lifetimes: {
    attached() {
      this.setData({ unitId: adUnits[this.data.position] || '' });
    }
  },

  methods: {
    hide() {
      this.setData({ hidden: true });
    }
  }
});
