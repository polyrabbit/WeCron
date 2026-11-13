// API server per environment. Preview on a real phone needs an address the phone can reach,
// the simulator can use localhost.
const BASE_URLS = {
  develop: 'http://localhost:8000',
  trial: 'https://wecron.betacat.io',
  release: 'https://wecron.betacat.io'
};

// Banner ad unit IDs, empty to disable
const AD_UNITS = {
  list: '',
  detail: '',
  settings: ''
};

// Development only, from a local file that is not committed, e.g. { baseUrl: 'http://192.168.1.10:8000' }
let local = {};
try {
  local = require('./config.local');
} catch (e) {
  // No local overrides
}

function getEnvVersion() {
  try {
    return wx.getAccountInfoSync().miniProgram.envVersion || 'release';
  } catch (e) {
    return 'release';
  }
}

const envVersion = getEnvVersion();

module.exports = {
  baseUrl: (envVersion === 'develop' && local.baseUrl) || BASE_URLS[envVersion] || BASE_URLS.release,
  adUnits: AD_UNITS
};
