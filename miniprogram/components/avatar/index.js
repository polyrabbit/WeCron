// Avatar of a user: the picture when it is known, otherwise the first character of the nickname on a colour
// derived from the name
const { initialOf, colourOf } = require('../../utils/avatar');

Component({
  properties: {
    // Avatar URL, WeChat no longer returns one for most users
    src: String,
    name: String,
    // Size in rpx
    size: { type: Number, value: 80 }
  },

  data: {
    failed: false,
    initial: '?',
    colour: '#4a7bd0'
  },

  observers: {
    name(name) {
      this.setData({ initial: initialOf(name), colour: colourOf(name) });
    },
    src() {
      this.setData({ failed: false });
    }
  },

  methods: {
    onError() {
      this.setData({ failed: true });
    }
  }
});
