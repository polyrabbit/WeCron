// Avatar of a user, derived from the nickname only, so nothing has to be stored or generated on the server
const PALETTE = ['#4a7bd0', '#5a9e6f', '#c9773f', '#8a73c4', '#4d9aa8', '#c2605e', '#7a8a3f', '#a06ab4'];

// First character of the name, emoji included
function initialOf(name) {
  const chars = Array.from((name || '').trim());
  return chars.length ? chars[0].toUpperCase() : '?';
}

function colourOf(name) {
  let hash = 0;
  for (const ch of String(name || '')) {
    hash = (hash * 31 + ch.codePointAt(0)) % 100000;
  }
  return PALETTE[hash % PALETTE.length];
}

module.exports = { initialOf, colourOf };
