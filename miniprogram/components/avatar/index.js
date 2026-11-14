// Avatar of a user: the picture when it is known, otherwise the first character of the nickname,
// or a person icon for users without one
const { initialOf, colourOf } = require('../../utils/avatar');

Component({
  properties: {
    // Avatar URL, WeChat no longer returns one for most users
    src: String,
    name: String,
    // User id, picks the background colour
    uid: String,
    // Size in rpx
    size: { type: Number, value: 80 }
  },

  data: {
    failed: false,
    initial: '',
    colour: '#4a7bd0'
  },

  observers: {
    'name, uid'(name, uid) {
      this.setData({ initial: initialOf(name), colour: colourOf(uid || name) });
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
