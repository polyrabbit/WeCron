const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

// Ordered as shown in the picker
const REPEAT_NAMES = { year: '年', month: '月', day: '天', week: '周', hour: '小时', minute: '分钟' };

const DEFER_UNITS = [
  { label: '分钟', value: 1 },
  { label: '小时', value: 60 },
  { label: '天', value: 24 * 60 },
  { label: '周', value: 7 * 24 * 60 }
];

function pad(n) {
  return n < 10 ? '0' + n : '' + n;
}

function formatTime(ts) {
  const d = new Date(ts);
  return pad(d.getHours()) + ':' + pad(d.getMinutes());
}

function formatDate(ts) {
  const d = new Date(ts);
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
}

function chineseDate(d) {
  return d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日';
}

// e.g. "11月12日(今天) 周四", the year is omitted for the current year
function groupTitle(ts, now = new Date()) {
  const d = new Date(ts);
  const dayDiff = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()) -
    new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000);
  let title = chineseDate(d);
  const relative = { '-1': '(昨天)', 0: '(今天)', 1: '(明天)' }[dayDiff];
  if (relative) title += relative;
  if (d.getFullYear() === now.getFullYear()) title = title.replace(d.getFullYear() + '年', '');
  return title + ' ' + WEEKDAYS[d.getDay()];
}

function groupByDate(reminds) {
  const groups = [];
  const index = {};
  const now = new Date();
  reminds.forEach((remind) => {
    const title = groupTitle(remind.time, now);
    if (!(title in index)) {
      index[title] = groups.length;
      groups.push({ title, reminds: [] });
    }
    groups[index[title]].reminds.push(remind);
  });
  return groups.sort((a, b) => a.reminds[0].time - b.reminds[0].time);
}

// The first non-zero key wins
function getRepeat(repeat) {
  repeat = repeat || {};
  for (const key in repeat) {
    if (REPEAT_NAMES[key] && repeat[key]) return { key, count: repeat[key] };
  }
  return null;
}

function formatRepeat(repeat) {
  const r = getRepeat(repeat);
  return r ? '每' + r.count + REPEAT_NAMES[r.key] : '不重复';
}

// The largest unit dividing the deferred minutes, null when there is no defer
function deferUnit(defer) {
  return defer ? DEFER_UNITS.slice().reverse().find((u) => defer % u.value === 0) : null;
}

function formatDefer(defer) {
  const unit = deferUnit(defer);
  return unit ? (defer < 0 ? '提前' : '延后') + Math.abs(defer / unit.value) + unit.label : '准时';
}

// Avatars may be served over http, which is blocked, the avatar component falls back to a letter
function avatar(url) {
  return url ? url.replace(/^http:\/\//, 'https://') : '';
}

module.exports = {
  REPEAT_NAMES,
  DEFER_UNITS,
  formatTime,
  formatDate,
  groupTitle,
  groupByDate,
  getRepeat,
  formatRepeat,
  deferUnit,
  formatDefer,
  avatar
};
