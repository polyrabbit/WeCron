// Avatar and name of a user, derived on the client so nothing has to be stored or generated on the server
const PALETTE = ['#4a7bd0', '#5a9e6f', '#c9773f', '#8a73c4', '#4d9aa8', '#c2605e', '#7a8a3f', '#a06ab4'];

// First character of the name, emoji included, empty when there is no name
function initialOf(name) {
  const chars = Array.from((name || '').trim());
  return chars.length ? chars[0].toUpperCase() : '';
}

// Keyed by the user id, so a user keeps the colour after renaming
function colourOf(key) {
  let hash = 0;
  for (const ch of String(key || '')) {
    hash = (hash * 31 + ch.codePointAt(0)) % 100000;
  }
  return PALETTE[hash % PALETTE.length];
}

// WeChat no longer tells nicknames, most users have none until they set one
function nameOf(user, isMe, fallback) {
  const name = user && user.nickname ? user.nickname.trim() : '';
  return name || (isMe ? '我' : fallback || '微信用户');
}

module.exports = { initialOf, colourOf, nameOf };
