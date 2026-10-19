// Lorekeeper's local editor: one module, no dependency or build step. Every change goes
// through the ops API with the version and values it was read from, so no edit is lost.
const $ = (id) => document.getElementById(id);
const meta = (name) => document.querySelector(`meta[name="${name}"]`).content;
const token = meta('lore-token');
const saga = meta('lore-saga') === 'true';
const calendars = JSON.parse(meta('lore-calendars'));
const worldName = meta('lore-name');

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const CATEGORIES = ['person', 'place', 'event', 'group', 'thing', 'narrative'];
const LIST_KEYS = new Set(['tags', 'aliases']);
const TIMING = new Set(['after', 'same_start', 'same_end', 'sf', 'starts_after_start', 'ends_after_end']);   // order, not relationship
const DRAG_THRESHOLD = 6;   // screen pixels; a click with a small wobble never re-dates an item
const TITLES = {
  BAD_ENCODING: 'File is not saved as UTF-8 text', BAD_FRONTMATTER: 'The fields at the top of a file can’t be read',
  UNSUPPORTED_FRONTMATTER: 'A field line was kept but not understood', DUPLICATE_ID: 'Two items share an ID',
  DUPLICATE_NAME: 'Two items share a name', UNKNOWN_TYPE: 'Unknown kind of item', BROKEN_LINK: 'Link to something that doesn’t exist',
  ROLE_TYPE: 'Link to the wrong kind of item', DATE_UNPARSED: 'A date Lorekeeper can’t read', DEPENDENCY_UNDATED: 'Timing link without a date',
  DEPENDENCY: 'Out of order with a linked item', DEAD_PARTICIPANT: 'Takes part after their death', UNBORN_PARTICIPANT: 'Takes part before their birth',
  AGE_LIMIT: 'Older than anyone could be', PARENT_AGE: 'Parent too young at the birth', TWO_PLACES: 'In two places at once',
  ORDER_REGRESSION: 'Goes back in time against its order', MAX_DURATION: 'Lasts longer than allowed', GAP: 'Wrong gap between linked items',
  STORY_ORDER: 'Story order moves back in time', END_BEFORE_START: 'Ends before it starts', AMBIGUOUS_NAME: 'One name points to two items',
  STAMP_UNREADABLE: 'A chapter stamp can’t be read', STAMP_RANGE: 'A chapter range ends before it starts',
  STORY_PAGE_UNREADABLE: 'A story page can’t be used',
};
const ICONS = {plus: 'M12 5v14M5 12h14', minus: 'M5 12h14', fit: 'M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5',
  close: 'M6 6l12 12M18 6 6 18', left: 'M15 6l-6 6 6 6', right: 'M9 6l6 6-6 6'};

const drafts = new Map(), cells = new Map(), conversions = new Map(), ages = new Map(), scrolls = new Map();
let graph = {items: [], links: [], types: {}, roles: {}, properties: {}};
let byPath = new Map(), partOf = new Map(), findPaths = new Map(), findText = new Map();
let selected = '', tab = 'Timeline', range = null, lastStamp = null;
let refreshing = false, dragging = false, offline = false, renderPending = false;
let refreshQueue = Promise.resolve(), checkTimer = null;
const ui = {people: '', hidden: new Set(), sheetText: '', sheetType: '', sheetLimit: 300, sort: ['name', 1], findings: null, allFindings: false,
  checking: false, recheck: false, checkError: null, checkedAt: null, flash: null};

// ---- small helpers -----------------------------------------------------------------------
function el(tag, text, attributes = {}) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  for (const [key, value] of Object.entries(attributes)) if (value != null) node.setAttribute(key, value);
  return node;
}
function svgEl(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) if (value != null) node.setAttribute(key, value);
  if (text != null) node.textContent = text;
  return node;
}
const add = (parent, child) => { parent.append(child); return child; };
function icon(name) {
  const node = svgEl('svg', {class: 'icon', viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false'});
  node.append(svgEl('path', {d: ICONS[name]}));
  return node;
}
function button(content, action, attributes = {}) {
  const node = el('button', null, {type: 'button', ...attributes});
  node.append(...[content].flat());
  node.addEventListener('click', () => Promise.resolve().then(action).catch(error => report(error)));
  return node;
}
const words = (key) => { const text = String(key).replace(/_/g, ' ').trim(); return text.charAt(0).toUpperCase() + text.slice(1); };
const plural = (n, one, many = one + 's') => `${n} ${n === 1 ? one : many}`;
const ref = (item) => `path:${item.path}`;
const typeInfo = (type) => graph.types[type] || {};
const typeLabel = (type) => typeInfo(type).label || words(type);
const typePlural = (type) => { const p = typeInfo(type).plural; return p && p !== type ? p : typeLabel(type); };
const category = (item) => CATEGORIES.includes(typeInfo(item.type).category) ? typeInfo(item.type).category : 'other';
const isPerson = (item) => typeInfo(item.type).category === 'person';
const isRole = (key) => Object.hasOwn(graph.roles, key);
const isDateKey = (key) => graph.properties[key]?.format === 'date' || ['born', 'died', 'date', 'end', 'start'].includes(key);
const label = (key) => ({canonical_name: 'Name', name: 'Name', type: 'Type', id: 'ID'})[key]
  || graph.properties[key]?.label || graph.roles[key]?.label || words(key);
// A link A -role-> B, seen from B: the role's stated inverse, else 'Sibling of' (B is A's sibling).
const inverseLabel = (role) => graph.roles[role]?.inverse || (/^\w+$/.test(label(role)) ? `${label(role)} of` : `${label(role)} (from)`);
const startKey = (item) => ['born', 'date', 'start'].find(k => item.fields[k]) || (isPerson(item) ? 'born' : 'date');
const endKey = (item) => ['died', 'end'].find(k => item.fields[k]) || (isPerson(item) ? 'died' : 'end');
const nameKey = (item) => item.fields.canonical_name != null ? 'canonical_name' : 'name';
const display = (value) => Array.isArray(value) ? value.join('\n') : String(value ?? '');
const byName = (a, b) => a.name.localeCompare(b.name, undefined, {numeric: true, sensitivity: 'base'});
const typeRank = (type) => { const i = CATEGORIES.indexOf(typeInfo(type).category); return i < 0 ? CATEGORIES.length : i; };
const typeOrder = (a, b) => typeRank(a) - typeRank(b) || typeLabel(a).localeCompare(typeLabel(b));
const dated = () => graph.items.filter(i => i.lo != null).sort((a, b) => a.lo - b.lo || byName(a, b));
const people = () => graph.items.filter(isPerson).sort(byName);
const events = () => dated().filter(i => !isPerson(i));
const takesPart = (person, event) => partOf.get(person.path)?.has(event.path) || false;
// The engine gives every dated event an end (its start, if none is written); only a written one counts here.
const hasEnd = (item) => Boolean(item.fields[endKey(item)] || item.fields.duration);
const whenText = (item) => item.start ? item.start.text + (hasEnd(item) && item.end ? ` to ${item.end.text}` : '') : 'Undated';
const narrow = () => matchMedia('(max-width: 900px)').matches;
const typing = (node) => Boolean(node?.closest?.('input, textarea, select, [contenteditable="true"]'));
// ponytail: label width from the character count; measure text if long names collide in practice.
const labelWidth = (text) => text.length * 7 + 6;

// ---- status, messages and the API -------------------------------------------------------
class ApiError extends Error {
  constructor(code, message, data) { super(message); this.code = code; this.data = data || {}; }
}
function status(text, kind = 'ok') { const node = $('status'); node.textContent = text; node.dataset.kind = kind; }
const anyDirty = () => [...drafts.values()].some(dirty) || cells.size > 0;
function idle() {
  if (offline) status('Lost contact. Retrying…', 'error');
  else if (anyDirty()) status('Unsaved changes', 'dirty');
  else status('Up to date', 'ok');
}
function toast(message, {kind = 'info', actions = [], timeout} = {}) {
  const box = el('div', null, {class: `toast ${kind}`, role: kind === 'error' ? 'alert' : 'status'});
  const row = el('div', null, {class: 'toast-actions'});
  for (const [text, action] of actions) row.append(button(text, async () => { box.remove(); await action(); }));
  box.append(el('p', message), button([icon('close')], () => box.remove(), {class: 'quiet icon-only', 'aria-label': 'Dismiss message'}), row);
  const stack = $('toasts');
  stack.append(box);
  while (stack.childElementCount > 3) stack.firstElementChild.remove();
  // Messages stay while the pointer or focus is on them, so Undo never vanishes mid-reach.
  const wait = timeout ?? (kind === 'error' ? 0 : actions.length ? 10000 : 5000);
  let timer;
  const arm = () => { clearTimeout(timer); if (wait) timer = setTimeout(() => box.remove(), wait); };
  for (const name of ['pointerenter', 'focusin']) box.addEventListener(name, () => clearTimeout(timer));
  for (const name of ['pointerleave', 'focusout']) box.addEventListener(name, arm);
  arm();
  return box;
}
function explain(error) {
  const message = error.message || String(error);
  if (error.code === 'CONFLICT' && error.data?.current) {
    const now = Object.entries(error.data.current).map(([key, value]) =>
      `${label(key)} is now ${value == null || value === '' ? 'empty' : `“${display(value).replace(/\n/g, ', ')}”`}`).join('; ');
    return `This item was changed elsewhere while you were editing it (${now}). Your text is still here.`;
  }
  if (error.code === 'FORBIDDEN') return `Not allowed here: ${message}`;
  return message.charAt(0).toUpperCase() + message.slice(1);
}
function report(error, actions = [], heading = 'Not saved') {
  status(heading, 'error');
  toast(explain(error), {kind: 'error', actions});
}
async function api(name, args = {}) {
  let response;
  try {
    response = await fetch(`/api/${name}`, {method: 'POST', body: JSON.stringify(args),
      headers: {'Content-Type': 'application/json', 'X-Lore-Token': token}});
  } catch {
    throw new ApiError('OFFLINE', 'The editor has lost contact with Lorekeeper. Check that “lore serve” is still running in its terminal, then reload this page.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = result.error || {};
    throw new ApiError(err.code || String(response.status), err.message || response.statusText, err.data);
  }
  return result;
}

// ---- dates -------------------------------------------------------------------------------
// The axis uses Lorekeeper's integer minutes since 0001-01-01, not Unix milliseconds.
// civil/daysFromCivil mirror dates.civil_from_days/days_from_civil and work beyond JS Date's range.
function civil(days) {
  const n = days + 306, era = Math.floor(n / 146097), doe = n - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153), m = mp + (mp < 10 ? 3 : -9);
  return {y: yoe + era * 400 + (m <= 2 ? 1 : 0), m, d: doy - Math.floor((153 * mp + 2) / 5) + 1};
}
function daysFromCivil(y, m, d) {
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor(y / 400), yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  return era * 146097 + yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy - 306;
}
const yearText = (y) => y > 0 ? String(y) : `${1 - y} BC`;
function gregorian(minute, precision = 'day') {
  // Lorekeeper's written form: 1764 · 1764-07 · 1764-07-12 · 1764-07-12 09:30; BC as 44 BC · 0044-03-15 BC.
  const {y, m, d} = civil(Math.floor(minute / 1440)), pad = (n) => String(n).padStart(2, '0');
  const bc = y < 1, year = String(bc ? 1 - y : y).padStart(4, '0');
  if (precision === 'year') return bc ? `${1 - y} BC` : year;
  let out = `${year}-${pad(m)}`;
  if (precision !== 'month') {
    out += '-' + pad(d);
    const time = ((Math.floor(minute) % 1440) + 1440) % 1440;
    if (precision !== 'day') out += ` ${pad(Math.floor(time / 60))}:${pad(time % 60)}`;
  }
  return bc ? `${out} BC` : out;
}
// Older files may still hold astronomical years (-0043-03-15 is 15 March 44 BC); both forms are read.
const ISO = /^(-?\d{4,})(?:-(\d{2}))?(?:-(\d{2}))?(?:[ T](\d{2}):(\d{2}))?( BC)?$/;
function readGregorian(text) {
  const bc = /^(\d+) BC$/.exec(text);
  if (bc) return {y: 1 - Number(bc[1]), minutes: 0};
  const m = ISO.exec(text);
  if (!m) return null;
  return {y: m[6] ? 1 - Number(m[1]) : Number(m[1]), m: m[2] && Number(m[2]), d: m[3] && Number(m[3]),
    time: m[4] && `${m[4]}:${m[5]}`, minutes: m[4] ? Number(m[4]) * 60 + Number(m[5]) : 0};
}
function dateWords(text) {
  // Reads as words: 1764 · 44 BC · July 1764 · 12 July 1764 · 15 March 44 BC · 12 July 1764, 09:30.
  const g = readGregorian(text);
  if (!g) return text;
  const year = yearText(g.y);
  if (!g.m) return year;
  const month = MONTHS[g.m - 1];
  if (!g.d) return `${month} ${year}`;
  return `${g.d} ${month} ${year}` + (g.time ? `, ${g.time}` : '');
}
function minuteOf(text) {
  // The first minute of a Gregorian date as Lorekeeper writes it.
  const g = readGregorian(text);
  return g ? daysFromCivil(g.y, g.m || 1, g.d || 1) * 1440 + g.minutes : null;
}
function shiftDate(text, precision, delta) {
  const start = minuteOf(text);
  if (start == null) return null;
  const {y, m} = civil(Math.floor(start / 1440));
  if (precision === 'year') return gregorian(daysFromCivil(y + Math.round(delta / UNIT.year), 1, 1) * 1440, 'year');
  if (precision === 'month') {
    const k = y * 12 + m - 1 + Math.round(delta / UNIT.month), ny = Math.floor(k / 12);
    return gregorian(daysFromCivil(ny, k - ny * 12 + 1, 1) * 1440, 'month');
  }
  return gregorian(start + (precision === 'day' ? Math.round(delta / 1440) * 1440 : Math.round(delta)), precision);
}
const exact = (when) => when && !when.circa && !when.provisional && !when.note && when.from === when.to;
const isGregorian = (id) => (calendars.find(c => (c.id || c.type || 'gregorian') === id)?.type || (id === 'gregorian' ? 'gregorian' : '')) === 'gregorian';
function readBack(result) {
  const ids = Object.keys(result.calendars).sort((a, b) => (b === result.parsed_by) - (a === result.parsed_by));
  const parts = ids.map(id => {
    const {from, to} = result.calendars[id], words = isGregorian(id) ? dateWords : (t) => t;
    return from === to ? words(from) : `between ${words(from)} and ${words(to)}`;
  });
  return parts[0] + (parts.length > 1 ? ` (${parts.slice(1).join('; ')})` : '');
}
function convert(text) {
  if (!conversions.has(text)) {
    const pending = api('convert', {date: text});
    pending.catch(error => { if (error.code !== 'INVALID') conversions.delete(text); });
    conversions.set(text, pending);
  }
  return conversions.get(text);
}
async function updateReadback(node, text) {
  const value = text.trim();
  node.dataset.text = value;
  node.classList.remove('warn');
  if (!value) { node.textContent = ''; return; }
  try {
    const result = await convert(value);
    if (node.dataset.text === value) node.textContent = `Reads as ${readBack(result)}`;
  } catch (error) {
    if (node.dataset.text !== value || error.code !== 'INVALID') return;
    node.textContent = 'Lorekeeper can’t read this as a date. Try 1764, 1764-07, 12 July 1764 or ~1764.';
    node.classList.add('warn');
  }
}
function fuzzy(item) {
  const s = item.start || {};
  return Boolean(s.circa || s.provisional || item.fields.status === 'provisional' || s.from !== s.to ||
    item.fields.date_min || item.fields.date_max || (['year', 'month'].includes(s.precision) && !hasEnd(item)));
}

// ---- axis ticks ---------------------------------------------------------------------------
const UNIT = {minute: 1, hour: 60, day: 1440, month: 43830, year: 525949};
const LADDER = [[1, 'minute'], [5, 'minute'], [15, 'minute'], [30, 'minute'], [1, 'hour'], [3, 'hour'], [6, 'hour'],
  [12, 'hour'], [1, 'day'], [2, 'day'], [7, 'day'], [1, 'month'], [3, 'month'], [6, 'month']];
for (let size = 1; size <= 1e8; size *= 10) for (const k of [1, 2, 5]) LADDER.push([k * size, 'year']);
function ticks([lo, hi], pixels) {
  const span = hi - lo;
  const [n, unit] = LADDER.find(([k, u]) => k * UNIT[u] / span * pixels >= 96) || LADDER.at(-1);
  const out = [], short = (m) => MONTHS[m - 1].slice(0, 3), pad = (v) => String(v).padStart(2, '0');
  if (unit === 'year') {
    const last = civil(Math.floor(hi / 1440)).y + 1;
    // Round BC years in BC numbering (10 BC, not astronomical -10 = 11 BC).
    for (let y = civil(Math.floor(lo / 1440)).y; y <= last;) {
      const r = y <= 0 ? (1 - y) % n : (n - y % n) % n;
      if (r) { y += r; continue; }
      out.push({minute: daysFromCivil(y, 1, 1) * 1440, label: yearText(y)});
      y += n;
    }
  } else if (unit === 'month') {
    const first = civil(Math.floor(lo / 1440));
    for (let k = Math.ceil((first.y * 12 + first.m - 1) / n) * n; ; k += n) {
      const y = Math.floor(k / 12), m = k - y * 12 + 1, minute = daysFromCivil(y, m, 1) * 1440;
      if (minute > hi) break;
      out.push({minute, label: `${short(m)} ${yearText(y)}`});
    }
  } else {
    const size = n * UNIT[unit];
    for (let t = Math.ceil(lo / size) * size; t <= hi; t += size) {
      const {y, m, d} = civil(Math.floor(t / 1440)), clock = ((t % 1440) + 1440) % 1440;
      out.push({minute: t, label: unit === 'day' ? `${d} ${short(m)} ${yearText(y)}`
        : `${d} ${short(m)} ${pad(Math.floor(clock / 60))}:${pad(clock % 60)}`});
    }
  }
  return out.filter(t => t.minute >= lo && t.minute <= hi);
}

// ---- find, create, selection ---------------------------------------------------------------
function renderFind() {
  const counts = new Map();
  for (const item of graph.items) counts.set(item.name, (counts.get(item.name) || 0) + 1);
  findPaths = new Map(); findText = new Map();
  const options = [];
  for (const item of [...graph.items].sort(byName)) {
    const text = `${item.name} · ${typeLabel(item.type)}${counts.get(item.name) > 1 ? ` · ${item.path}` : ''}`;
    findPaths.set(text, item.path); findText.set(item.path, text);
    options.push(el('option', null, {value: text}));
  }
  $('find-list').replaceChildren(...options);
}
function pickFind(loose) {
  const input = $('find'), text = input.value.trim(), q = text.toLowerCase();
  let path = findPaths.get(text);
  if (!path && loose && q) path = (graph.items.find(i => i.name.toLowerCase() === q) || graph.items.find(i => i.name.toLowerCase().includes(q)))?.path;
  if (!path) { if (loose && q) toast(`Nothing called “${text}” in this world.`); return; }
  input.value = '';
  selectItem(path, {reveal: true, focus: 'title'});
}
function renderCreateTypes() {
  const select = $('create-type'), previous = select.value;
  select.replaceChildren(...Object.keys(graph.types).sort(typeOrder).map(t => el('option', typeLabel(t), {value: t})));
  select.value = previous || (graph.types.character ? 'character' : Object.keys(graph.types).sort(typeOrder)[0]);
}
function openCreate(type) {
  // After the current click: the outside-click handler would otherwise close it at once.
  setTimeout(() => {
    $('new-item').open = true;
    if (type && graph.types[type]) $('create-type').value = type;
    $('create-name').focus();
  });
}
function selectItem(path, {focus = false, reveal = false, show = false} = {}) {
  selected = path;
  const item = byPath.get(path);
  if (reveal && item) revealInView(item);
  renderInspector();
  markSelection();
  if (focus === 'title') $('inspector-title')?.focus();
  else if (focus) $('inspector').querySelector('input:not([readonly]), select, textarea')?.focus();
  // On a phone the inspector sits below the view: bring it up when an item is chosen there.
  if ((reveal || show) && narrow()) $('inspector-panel').scrollIntoView({block: 'start'});
}
function markSelection() {
  const view = $('view');
  view.querySelectorAll('[data-path]').forEach(node => {
    const on = node.dataset.path === selected;
    node.classList.toggle('selected', on);
    if (node.matches('svg .item')) node.setAttribute('aria-current', String(on));
  });
  const svg = view.querySelector('#time-chart');
  if (svg) {
    const nodes = [...svg.querySelectorAll('.item')];
    const current = nodes.find(n => n.dataset.path === selected) || nodes[0];
    nodes.forEach(n => n.setAttribute('tabindex', n === current ? '0' : '-1'));
  }
}
function revealInView(item) {
  if (['Timeline', 'Subway'].includes(tab) && item.lo != null) {
    if (tab === 'Timeline' && ui.hidden.delete(item.type)) range = null;
    if (!range) fit();
    if (item.hi < range[0] || item.lo > range[1]) {
      const span = range[1] - range[0], middle = (item.lo + item.hi) / 2;
      range = [middle - span / 2, middle + span / 2];
    }
    renderView();
  }
  requestAnimationFrame(() => $('view').querySelector(`[data-path="${CSS.escape(item.path)}"]`)?.scrollIntoView({block: 'nearest', inline: 'nearest'}));
}

// ---- inspector ----------------------------------------------------------------------------
function dirty(draft) { return Boolean(draft && (Object.keys(draft.values).length > 0 || draft.note)); }
const isList = (key, original) => Array.isArray(original) || (original === undefined && LIST_KEYS.has(key));
function valueOf(text, original, key) {
  if (!isList(key, original)) return text.trim();
  return text.split('\n').map(v => v.trim()).filter(Boolean);
}
// An inspector draft is {base: the item when editing began (its version guards the save), seen: each edited
// key's value when its edit began (the expectation sent), values: the edited text}. Unedited fields show the
// latest copy, so live reloads stay visible without weakening the conflict check.
const seenOr = (draft, key) => Object.hasOwn(draft.seen, key) ? draft.seen[key] : latestOf(draft.base).fields[key];
function changes(draft) {
  const field = {}, unset = [];
  for (const [key, text] of Object.entries(draft.values)) {
    const original = seenOr(draft, key), value = valueOf(text, original, key);
    if (Array.isArray(value) ? value.length : value) field[key] = value;
    else if (key === nameKey(draft.base)) throw new ApiError('INVALID', 'An item needs a name.');
    else if (original !== undefined) unset.push(key);
  }
  return {field, unset};
}
function fieldsFor(item) {
  // Local mode edits links through Connections; saga mode proposes them as field text.
  const keys = [nameKey(item), 'type', startKey(item), endKey(item), ...Object.keys(item.fields)];
  return [...new Set(keys)].filter(k => k !== 'id' && (saga || !isRole(k)));
}
function renderInspector() {
  const panel = $('inspector'), focusId = panel.contains(document.activeElement) ? document.activeElement.id : null;
  const item = byPath.get(selected);
  panel.replaceChildren();
  if (!item) { panel.append(inspectorWelcome()); return; }
  let draft = drafts.get(item.path);
  if (!dirty(draft)) { draft = {base: item, seen: {}, values: Object.create(null), note: '', extra: draft?.extra || []}; drafts.set(item.path, draft); }

  const head = el('div', null, {class: 'inspector-head'});
  head.append(button([icon('left'), 'Back to the view'], () => {
    $('view').scrollIntoView({block: 'start'});
    $('view').querySelector(`[data-path="${CSS.escape(item.path)}"]`)?.focus?.();
  }, {class: 'quiet back-to-view'}));
  head.append(el('h2', item.name, {id: 'inspector-title', tabindex: '-1'}));
  const info = el('div', null, {class: 'meta'});
  info.append(el('span', typeLabel(item.type), {class: `kind cat-${category(item)}`}));
  if (item.fields.id) info.append(el('span', item.fields.id, {class: 'path', title: 'ID'}));
  info.append(el('span', item.path, {class: 'path', title: 'File'}));
  head.append(info);
  panel.append(head);

  const form = el('form', null, {id: 'edit-form', novalidate: ''});
  const save = el('button', saga ? 'Propose change' : 'Save', {type: 'submit', class: 'primary', id: 'save-item'});
  const discard = button('Discard changes', () => { drafts.delete(item.path); renderInspector(); idle(); }, {id: 'discard-item', class: 'quiet'});
  const sync = () => { save.disabled = discard.disabled = !dirty(draft); idle(); };
  const keys = [...new Set([...fieldsFor(item), ...draft.extra])];
  for (const key of keys) form.append(fieldRow(draft, key, sync));
  form.append(addFieldRow(draft, keys));
  if (saga) {
    const wrap = el('div', null, {class: 'field'});
    const note = el('textarea', null, {id: 'change-note', required: '', 'aria-describedby': 'change-note-hint'});
    note.value = draft.note;
    note.addEventListener('input', () => { draft.note = note.value; sync(); });
    wrap.append(el('label', 'Change note', {for: 'change-note'}), note,
      el('p', 'Say what should change and why. The pipeline applies it later; the story files stay as they are.', {class: 'hint', id: 'change-note-hint'}));
    form.append(wrap);
  }
  const actions = el('div', null, {class: 'actions'});
  actions.append(save, discard, el('span', saga ? '' : 'Ctrl+S saves', {class: 'hint'}));
  form.append(actions);
  form.addEventListener('submit', event => { event.preventDefault(); saveInspector(draft); });
  panel.append(form);
  sync();
  renderLinks(panel, item);
  if (focusId) $(focusId)?.focus({preventScroll: true});
}
function fieldRow(draft, key, sync) {
  const original = seenOr(draft, key), id = `field-${key}`;
  const wrap = el('div', null, {class: 'field'});
  const current = key in draft.values ? draft.values[key] : display(original);
  let input;
  if (key === 'type') {
    input = el('select', null, {id, name: key});
    for (const type of Object.keys(graph.types).sort(typeOrder)) input.append(el('option', typeLabel(type), {value: type}));
    if (!graph.types[original]) input.append(el('option', `${original} (not in this project’s types)`, {value: original}));
  } else if (isList(key, original)) {
    input = el('textarea', null, {id, name: key, rows: String(Math.min(8, Math.max(2, current.split('\n').length + 1)))});
  } else {
    input = el('input', null, {id, name: key, autocomplete: 'off', spellcheck: isDateKey(key) ? 'false' : null});
  }
  input.value = current;
  wrap.append(el('label', label(key), {for: id}), input);
  if (input.tagName === 'TEXTAREA') {
    wrap.append(el('p', 'One per line.', {class: 'hint', id: `${id}-hint`}));
    input.setAttribute('aria-describedby', `${id}-hint`);
  }
  const mark = () => wrap.classList.toggle('changed', key in draft.values);
  input.addEventListener(key === 'type' ? 'change' : 'input', () => {
    if (!Object.hasOwn(draft.seen, key)) draft.seen[key] = original;
    if (input.value === display(draft.seen[key])) { delete draft.values[key]; delete draft.seen[key]; }
    else draft.values[key] = input.value;
    mark(); sync();
  });
  mark();
  if (isDateKey(key)) {
    const echo = el('p', null, {class: 'readback', id: `${id}-readback`, 'aria-live': 'polite'});
    input.setAttribute('aria-describedby', echo.id);
    wrap.append(echo);
    let timer;
    input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => updateReadback(echo, input.value), 350); });
    updateReadback(echo, input.value);
  }
  return wrap;
}
function addFieldRow(draft, keys) {
  const row = el('div', null, {class: 'add-field'});
  const pick = el('select', null, {id: 'add-field', 'aria-label': 'Add a field'});
  pick.append(el('option', 'Add a field…', {value: ''}));
  const candidates = new Set([...Object.keys(graph.properties), ...LIST_KEYS]);
  for (const key of candidates) if (!keys.includes(key) && key !== 'id' && (saga || !isRole(key))) pick.append(el('option', label(key), {value: key}));
  pick.append(el('option', 'Another field…', {value: '*'}));
  const custom = el('input', null, {id: 'add-field-name', placeholder: 'field name, e.g. eye colour', hidden: '', 'aria-label': 'New field name'});
  const add = (key) => { draft.extra = [...draft.extra, key]; renderInspector(); $(`field-${key}`)?.focus(); };
  pick.addEventListener('change', () => {
    if (pick.value === '*') { custom.hidden = false; custom.focus(); }
    else if (pick.value) add(pick.value);
  });
  custom.addEventListener('keydown', event => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    const key = custom.value.trim().toLowerCase().replace(/[\s-]+/g, '_');
    const managed = ['id', 'type', 'canonical_name', 'name'].includes(key);
    if (/^[a-z_]+$/.test(key) && !keys.includes(key) && !managed) add(key);
    else {
      custom.classList.add('failed'); custom.setAttribute('aria-invalid', 'true');
      toast(managed ? 'Lorekeeper manages that field itself.' : keys.includes(key) ? 'That field is already here.'
        : 'Field names use letters and spaces only.', {kind: 'error'});
    }
  });
  row.append(pick, custom);
  return row;
}
const snapshot = (item, keys) => Object.fromEntries(keys.map(k => [k, item.fields[k] ?? null]));
async function saveInspector(draft) {
  const item = draft.base;
  if (draft.saving) return;   // a second Ctrl+S would send the old version and conflict with the first
  let field, unset;
  try { ({field, unset} = changes(draft)); } catch (error) { report(error); return; }
  if (!Object.keys(field).length && !unset.length && !(saga && draft.note)) return;
  if (saga && !draft.note.trim()) {
    toast('Add a change note that says what should change and why.', {kind: 'error'});
    $('change-note')?.focus();
    return;
  }
  const controls = [...$('inspector').querySelectorAll('input, select, textarea, button')];
  const focusId = $('inspector').contains(document.activeElement) ? document.activeElement.id : null;
  draft.saving = true;
  controls.forEach(c => { c.disabled = true; });
  status(saga ? 'Sending…' : 'Saving…', 'busy');
  const keys = [...Object.keys(field), ...unset], before = Object.fromEntries(keys.map(k => [k, draft.seen[k] ?? null]));
  try {
    if (saga) {
      await api('request', {item: ref(item), field, unset, note: draft.note, version: item.version, expect: before});
      drafts.delete(item.path);
      toast(`Change to ${item.name} proposed. The story files stay as they are until the pipeline applies it.`);
    } else {
      const result = await api('set', {item: ref(item), field, unset, version: item.version, expect: before});
      drafts.delete(item.path);
      offerUndo(item, before, {...field, ...Object.fromEntries(unset.map(k => [k, null]))}, result,
        result.merged ? `Saved ${item.name}, merged with other changes made on disk.` : `Saved ${item.name}.`);
    }
    await refresh();
    renderInspector();
    idle();
  } catch (error) {
    report(error, error.data?.current ? conflictActions(item.path) : []);
  } finally {
    draft.saving = false;
    controls.forEach(c => { if (c.isConnected) c.disabled = false; });
    if ($('save-item')?.isConnected && drafts.has(item.path)) $('save-item').disabled = $('discard-item').disabled = !dirty(drafts.get(item.path));
    if (focusId && !$('inspector').contains(document.activeElement)) $(focusId)?.focus({preventScroll: true});
  }
}
function offerUndo(item, before, after, result, message) {
  idle();
  toast(message, {actions: [['Undo', async () => {
    const field = {}, unset = [];
    for (const [key, value] of Object.entries(before)) value == null ? unset.push(key) : (field[key] = value);
    status('Undoing…', 'busy');
    await api('set', {item: ref(item), field, unset, version: result.version, expect: after});
    await refresh(); renderInspector(); idle();
    toast(`Undid the change to ${item.name}.`);
  }]]});
}
function conflictActions(path) {
  return [
    ['Load their version', async () => { drafts.delete(path); await refresh(); renderInspector(); idle(); }],
    ['Keep my text', async () => {
      const draft = drafts.get(path);
      await refresh();
      const latest = byPath.get(path);
      if (draft && latest) { draft.base = latest; for (const key of Object.keys(draft.values)) draft.seen[key] = latest.fields[key]; }
      renderInspector();
      status('Your text is kept. Review it, then save.', 'dirty');
    }],
  ];
}
async function linkChange(op, item, role, target, message) {
  const before = item.fields[role];
  const result = await api(op, {item: ref(item), role, target, version: item.version});
  await refresh(); renderInspector();
  const after = byPath.get(item.path)?.fields[role];
  if (!$('inspector').contains(document.activeElement)) ($('link-target') || $('inspector-title'))?.focus({preventScroll: true});
  toast(message, {actions: [['Undo', async () => {
    await api('set', {item: ref(item), ...(before === undefined ? {unset: [role]} : {field: {[role]: before}}),
      version: result.version, expect: {[role]: after ?? null}});
    await refresh(); renderInspector();
    toast('Undone.');
  }]]});
}
function groupBy(list, key) {
  const out = new Map();
  for (const entry of list) { const k = key(entry); if (!out.has(k)) out.set(k, []); out.get(k).push(entry); }
  return out;
}
function renderLinks(panel, item) {
  const section = el('section', null, {'aria-labelledby': 'links-title'});
  section.append(el('h3', 'Connections', {id: 'links-title'}));
  const outgoing = graph.links.filter(l => l.from_path === item.path);
  if (!outgoing.length) section.append(el('p', saga ? 'No connections.' : 'No connections yet.', {class: 'hint'}));
  for (const [role, links] of groupBy(outgoing, l => l.role)) {
    section.append(el('h4', label(role), {class: 'role-name'}));
    const list = el('ul', null, {class: 'links'});
    for (const link of links) {
      const target = byPath.get(link.to_path), name = target?.name || link.to, row = el('li'), left = el('span');
      left.append(target ? button(name, () => selectItem(target.path, {reveal: true}), {class: 'link'}) : el('span', name));
      if (!link.resolved) left.append(' ', el('span', 'not found', {class: 'missing'}));
      if (link.lag) left.append(' ', el('span', String(link.lag), {class: 'hint'}));
      row.append(left);
      if (!saga) row.append(button([icon('close')], () => linkChange('unlink', item, role, target ? ref(target) : link.to,
        `Removed ${name} from ${label(role)}.`), {class: 'quiet icon-only', title: 'Remove this connection',
        'aria-label': `Remove ${name} from ${label(role)}`, id: `unlink-${encodeURIComponent(`${role}\0${link.to_path || link.to}`)}`}));
      list.append(row);
    }
    section.append(list);
  }
  panel.append(section);
  if (saga) panel.append(el('p', 'To propose a connection, edit its field above (for example [[Name]]) or describe it in the change note.', {class: 'hint'}));
  else panel.append(addLinkForm(item));

  const incoming = graph.links.filter(l => l.to_path === item.path && l.resolved);
  const back = el('section', null, {'aria-labelledby': 'backlinks-title'});
  back.append(el('h3', 'Linked from', {id: 'backlinks-title'}));
  if (!incoming.length) back.append(el('p', 'Nothing links here yet.', {class: 'hint'}));
  for (const [role, links] of groupBy(incoming, l => l.role)) {
    const group = el('details', null, links.length <= 6 ? {open: ''} : {});
    group.append(el('summary', `${inverseLabel(role)} · ${links.length}`));
    const list = el('ul', null, {class: 'links'});
    for (const link of links) {
      const source = byPath.get(link.from_path);
      if (source) add(list, el('li')).append(button(source.name, () => selectItem(source.path, {reveal: true}), {class: 'link'}));
    }
    group.append(list);
    back.append(group);
  }
  panel.append(back);
}
function addLinkForm(item) {
  const box = el('section', null, {class: 'add-link', 'aria-labelledby': 'add-link-title'});
  box.append(el('h3', 'Add a connection', {id: 'add-link-title'}));
  const roles = el('select', null, {id: 'link-role'});
  for (const [key, role] of Object.entries(graph.roles)) roles.append(el('option', role.label || words(key), {value: key}));
  const target = el('input', null, {id: 'link-target', list: 'link-targets', placeholder: 'Type a name', autocomplete: 'off', 'aria-describedby': 'link-scope'});
  const scope = el('p', null, {class: 'hint', id: 'link-scope'});
  const options = el('datalist', null, {id: 'link-targets'}), choices = new Map();
  const fill = () => {
    const allowed = graph.roles[roles.value]?.to || [];
    choices.clear();
    options.replaceChildren();
    for (const other of [...graph.items].sort(byName)) {
      if (other.path === item.path || (allowed.length && !allowed.includes(other.type))) continue;
      choices.set(findText.get(other.path), other);
      options.append(el('option', null, {value: findText.get(other.path)}));
    }
    scope.textContent = allowed.length ? `Only ${allowed.map(typePlural).join(' or ').toLowerCase()}.` : '';
  };
  const add = async () => {
    const text = target.value.trim(), q = text.toLowerCase();
    const other = choices.get(text) || [...choices.values()].find(o => o.name.toLowerCase() === q);
    if (!other) {
      target.classList.add('failed'); target.setAttribute('aria-invalid', 'true');
      toast(text ? `Choose “${text}” from the list, or check its spelling.` : 'Type a name and choose it from the list.', {kind: 'error'});
      target.focus();
      return;
    }
    await linkChange('link', item, roles.value, ref(other), `Added ${other.name} to ${label(roles.value)}.`);
    $('link-target')?.focus();
  };
  roles.addEventListener('change', () => { fill(); target.value = ''; });
  target.addEventListener('input', () => { target.classList.remove('failed'); target.removeAttribute('aria-invalid'); });
  target.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); add().catch(error => report(error)); } });
  fill();
  const row = el('div', null, {class: 'row'});
  row.append(target, button('Add', add, {id: 'add-link'}));
  box.append(el('label', 'Connection', {for: 'link-role'}), roles, el('label', 'To', {for: 'link-target'}), row, scope, options);
  return box;
}
function inspectorWelcome() {
  const box = el('div', null, {class: 'welcome'});
  box.append(el('h2', 'Inspector', {id: 'inspector-title', tabindex: '-1'}),
    el('p', 'Select an item in any view to see and edit its details here.'),
    el('p', 'Press / to find an item by name.', {class: 'hint'}));
  return box;
}

// ---- views --------------------------------------------------------------------------------
function scrollBox(kind) { return el('div', null, {class: `scroll ${kind}`, 'data-tab': tab}); }
function emptyState(title, text, action) {
  const box = el('div', null, {class: 'empty'});
  box.append(el('h2', title), el('p', text));
  if (action) box.append(button(action[0], action[1], {class: 'primary'}));
  return box;
}
function welcome() {
  return saga ? emptyState(`${worldName} has no items yet`, 'Items appear here once the saga has some.')
    : emptyState(`Welcome to ${worldName}`, 'Your world is empty. Start with a character, a place or an event. You can add dates and connections afterwards.',
      ['Create your first item', () => openCreate('character')]);
}
function fit() {
  const items = dated().filter(i => tab !== 'Timeline' || !ui.hidden.has(i.type));
  if (!items.length) { range = [0, 525949]; return; }
  const lo = Math.min(...items.map(i => i.lo)), hi = Math.max(...items.map(i => i.hi));
  const pad = Math.max(1440, (hi - lo) * .04);
  range = [lo - pad, hi + pad];
}
function zoom(factor, anchor = .5) {
  if (!range) fit();
  const span = Math.min(5.3e14, Math.max(60, (range[1] - range[0]) * factor));
  const center = range[0] + (range[1] - range[0]) * anchor;
  range = [center - span * anchor, center + span * (1 - anchor)];
  scheduleRender();
}
function pan(fraction) {
  if (!range) fit();
  const shift = (range[1] - range[0]) * fraction;
  range = range.map(v => v + shift);
  scheduleRender();
}
function zoomControls() {
  const group = el('div', null, {class: 'group', role: 'group', 'aria-label': 'Zoom and move'});
  group.append(
    button([icon('minus')], () => zoom(2), {id: 'zoom-out', class: 'icon-only', 'aria-label': 'Zoom out', title: 'Zoom out (−)'}),
    button([icon('plus')], () => zoom(.5), {id: 'zoom-in', class: 'icon-only', 'aria-label': 'Zoom in', title: 'Zoom in (+)'}),
    button([icon('left')], () => pan(-.25), {id: 'pan-left', class: 'icon-only', 'aria-label': 'Move earlier', title: 'Move earlier'}),
    button([icon('right')], () => pan(.25), {id: 'pan-right', class: 'icon-only', 'aria-label': 'Move later', title: 'Move later'}),
    button([icon('fit'), 'Fit'], () => { fit(); renderView(); }, {id: 'fit-all', title: 'Fit everything (0)'}));
  return group;
}
function legend() {
  const box = el('div', null, {class: 'legend', 'aria-hidden': 'true'});
  for (const [kind, text] of [['', 'Exact'], ['fuzzy', 'Approximate'], ['life', 'Alive, no death recorded']]) {
    const sample = svgEl('svg', {viewBox: '0 0 26 14'}), g = svgEl('g', {class: `cat-event ${kind === 'life' ? '' : kind}`});
    g.append(kind === 'life' ? svgEl('rect', {x: 1, y: 5, width: 24, height: 4, rx: 2, class: 'life'})
      : svgEl('rect', {x: 1, y: 2, width: 24, height: 10, rx: 3, class: 'mark'}));
    sample.append(g);
    const entry = el('span');
    entry.append(sample, ` ${text}`);
    box.append(entry);
  }
  return box;
}
function chart(box, width, gutter = 0) {
  if (!range) fit();
  const left = gutter + 14, right = width - 14, span = range[1] - range[0];
  const x = (minute) => left + (minute - range[0]) / span * (right - left);
  const axis = svgEl('svg', {width, height: 30, 'aria-hidden': 'true'}), marks = ticks(range, right - left);
  let free = 0;
  for (const tick of marks) {
    const px = x(tick.minute), w = labelWidth(tick.label);
    axis.append(svgEl('line', {x1: px, x2: px, y1: 22, y2: 30, class: 'grid'}));
    if (px + 4 >= free && px + 4 + w <= width) { axis.append(svgEl('text', {x: px + 4, y: 17, class: 'tick-label'}, tick.label)); free = px + 4 + w + 8; }
  }
  const head = el('div', null, {class: 'axis'});
  head.append(axis);
  const svg = svgEl('svg', {width, role: 'group', id: 'time-chart'});
  box.append(head, svg);
  const px = (event) => event.clientX - svg.getBoundingClientRect().left;
  svg.addEventListener('wheel', event => {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      zoom(event.deltaY > 0 ? 1.25 : .8, Math.max(0, Math.min(1, (px(event) - left) / (right - left))));
    } else if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
      event.preventDefault();
      pan((event.deltaX || event.deltaY) / (right - left));
    }
  }, {passive: false});
  svg.addEventListener('pointerdown', event => {
    if (event.target.closest('.item') || event.button !== 0 || event.pointerType === 'touch') return;
    const start = event.clientX, initial = [...range];
    dragging = true; svg.setPointerCapture(event.pointerId);
    const cleanup = () => { dragging = false; svg.removeEventListener('pointerup', finish); svg.removeEventListener('pointercancel', cleanup); };
    const finish = (e) => {
      cleanup();
      if (Math.abs(e.clientX - start) < DRAG_THRESHOLD) return;
      const shift = (e.clientX - start) / (right - left) * (initial[1] - initial[0]);
      range = initial.map(v => v - shift);
      renderView();
    };
    svg.addEventListener('pointerup', finish); svg.addEventListener('pointercancel', cleanup);
  });
  const grid = (height) => {
    for (const tick of marks) { const p = x(tick.minute); svg.prepend(svgEl('line', {x1: p, x2: p, y1: 0, y2: height, class: 'grid'})); }
    svg.setAttribute('height', height);
  };
  return {svg, x, left, right, grid, px};
}
function wireItems(svg) {
  const nodes = [...svg.querySelectorAll('.item')];
  for (const node of nodes) {
    node.addEventListener('click', () => selectItem(node.dataset.path, {show: true}));
    node.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectItem(node.dataset.path, {focus: true}); return; }
      const i = nodes.indexOf(node);
      const next = {ArrowLeft: i - 1, ArrowUp: i - 1, ArrowRight: i + 1, ArrowDown: i + 1, Home: 0, End: nodes.length - 1}[event.key];
      if (next == null) return;
      event.preventDefault();
      const target = nodes[Math.max(0, Math.min(nodes.length - 1, next))];
      selectItem(target.dataset.path);
      target.focus();
    });
  }
}
function typeChips(types, items) {
  const box = el('div', null, {class: 'chips', role: 'group', 'aria-label': 'Show kinds of items'});
  for (const type of types) {
    const chip = el('label', null, {class: `chip cat-${category({type})}`});
    const box2 = el('input', null, {type: 'checkbox', id: `show-${type}`});
    box2.checked = !ui.hidden.has(type);
    box2.addEventListener('change', () => { box2.checked ? ui.hidden.delete(type) : ui.hidden.add(type); renderView(); });
    chip.append(box2, el('span', null, {class: 'swatch'}), `${typePlural(type)} · ${items.filter(i => i.type === type).length}`);
    box.append(chip);
  }
  return box;
}
function timeline(view) {
  const all = dated(), types = [...new Set(all.map(i => i.type))].sort(typeOrder);
  const bar = el('div', null, {class: 'toolbar'});
  bar.append(zoomControls(), el('span', null, {class: 'spacer'}), legend());
  view.append(bar);
  if (!all.length) {
    view.append(emptyState('Nothing is dated yet', 'Give an item a date, or a person a birth date, in the inspector and it appears here.'));
    return;
  }
  if (types.length > 1) view.append(typeChips(types, all));
  const box = scrollBox('chart');
  view.append(box);
  const width = Math.max(280, box.clientWidth), c = chart(box, width);
  c.svg.setAttribute('aria-label', 'Timeline. Use the arrow keys to move between items.');
  const ROW = 36, BAND = 30;
  // Someone with no recorded death is alive: their life line runs on to the latest date in the story.
  const storyEnd = Math.max(...all.map(i => i.hi));
  let y = 6;
  for (const type of types) {
    if (ui.hidden.has(type)) continue;
    const items = all.filter(i => i.type === type), rows = [], placed = [];
    for (const item of items) {
      const living = isPerson(item) && !hasEnd(item) && item.hi < storyEnd;
      const x0 = c.x(item.lo), x1 = c.x(item.hi), xl = living ? c.x(storyEnd) : x1;
      if (xl < c.left - 1 || x0 > c.right + 1) continue;
      const v0 = Math.max(c.left, x0), v1 = Math.min(c.right, x1), vl = Math.min(c.right, xl), w = labelWidth(item.name);
      const lx = Math.max(c.left, Math.min(v0, c.right - w)), start = Math.min(lx, v0) - 6, end = Math.max(vl, lx + w) + 12;
      let row = rows.findIndex(e => e <= start);
      if (row < 0) { row = rows.length; rows.push(0); }
      rows[row] = end;
      placed.push({item, row, x0, x1, v0, v1, vl, living, lx, start, end, w});
    }
    const outside = items.length - placed.length;
    c.svg.append(svgEl('text', {x: c.left, y: y + 18, class: 'band-label'}, typePlural(type)),
      svgEl('text', {x: c.left + labelWidth(typePlural(type)) + 6, y: y + 18, class: 'band-count'},
        `${items.length}${outside ? ` · ${outside} outside this view` : ''}`),
      svgEl('line', {x1: c.left, x2: c.right, y1: y + 25.5, y2: y + 25.5, class: 'band-rule'}));
    y += BAND;
    for (const p of placed) {
      const top = y + p.row * ROW, item = p.item, mid = top + 24;
      const when = whenText(item) + (p.living ? ', alive (no death recorded)' : '');
      const g = svgEl('g', {class: `item cat-${category(item)}${fuzzy(item) ? ' fuzzy' : ''}`, role: 'button', tabindex: '-1',
        'data-path': item.path, 'aria-label': `${item.name}, ${typeLabel(item.type)}, ${when}`,
        id: `timeline-${encodeURIComponent(item.path)}`});
      g.append(svgEl('rect', {class: 'hit', x: p.start, y: top + 1, width: p.end - p.start - 6, height: ROW - 3, rx: 5}),
        svgEl('text', {x: p.lx, y: top + 14, class: 'item-label'}, item.name));
      const lifeFrom = Math.max(c.left, p.x1);
      if (p.living && p.vl > lifeFrom) g.append(svgEl('rect', {x: lifeFrom, y: mid - 2, width: p.vl - lifeFrom, height: 4, rx: 2, class: 'life'}));
      g.append(
        p.x1 - p.x0 < 6 ? svgEl('circle', {cx: Math.max(c.left, Math.min(c.right, p.x0)), cy: mid, r: 5.5, class: 'mark'})
          : svgEl('rect', {x: p.v0, y: mid - 5, width: Math.max(2, p.v1 - p.v0), height: 10, rx: 3, class: 'mark'}),
        svgEl('title', {}, `${item.name} · ${when}`));
      if (!saga) enableRedate(g, item, c, {x: p.lx + p.w + 4, y: top + 14,
        bar: p.x1 - p.x0 < 6 ? null : {v0: p.v0, v1: p.v1, x0: p.x0, x1: p.x1, mid}});
      c.svg.append(g);
    }
    y += Math.max(1, rows.length) * ROW + 12;
  }
  c.grid(y);
  wireItems(c.svg);
  const undated = graph.items.length - all.length, note = el('p', null, {class: 'hint'});
  note.append(saga ? 'Select an item to propose a change. ' : 'Select an item to open it. Drag an exactly dated item sideways to move it, '
    + 'or drag either end of a bar to change just its start or end. ');
  if (undated) note.append(`${plural(undated, 'item')} without a date ${undated === 1 ? 'is' : 'are'} not shown; `,
    button('see them in the Spreadsheet', () => activateTab($('tab-spreadsheet')), {class: 'link'}), '.');
  view.append(note);
}
function enableRedate(g, item, c, at) {
  const s = item.start, e = item.fields[endKey(item)] ? item.end : null;
  // A drag moves the whole written span; anything it cannot move exactly is edited in the inspector instead.
  if (!exact(s) || item.fields.date_min || item.fields.date_max || (e && (!exact(e) || minuteOf(e.from) == null))) return;
  g.classList.add('draggable');
  // A bar with a written end gets a handle at each visible end: drag one to change just that date.
  const bar = e && at.bar && at.bar.v1 - at.bar.v0 >= 24 ? at.bar : null, mark = g.querySelector('.mark');
  if (bar) for (const [edge, x, text] of [['start', bar.x0, 'Drag to change the start'], ['end', bar.x1, 'Drag to change the end']]) {
    if (x < c.left || x > c.right) continue;
    const handle = svgEl('rect', {class: 'handle', 'data-edge': edge, x: edge === 'start' ? x - 1 : x - 9, y: bar.mid - 9, width: 10, height: 18, rx: 3});
    handle.append(svgEl('title', {}, text));
    g.append(handle);
  }
  g.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.pointerType === 'touch') return;
    event.stopPropagation();
    const edge = event.target.dataset?.edge || 'move', startX = event.clientX, initial = [...range];
    const minuteAt = (px) => initial[0] + (px - c.left) / (c.right - c.left) * (initial[1] - initial[0]);
    let allowed = false, moved = false;
    // Identify the parser before allowing movement, rather than guessing from the date's spelling.
    const units = ['year', 'month', 'day', 'minute'];
    const check = convert(s.text).then(r => {
      allowed = isGregorian(r.parsed_by) && units.includes(s.precision) && (!e || units.includes(e.precision));
      return allowed;
    });
    check.catch(() => {});
    // The new fields for a pointer position: the whole span, the start alone, or the end alone.
    const change = (ev) => {
      const dx = ev.clientX - startX;
      if (edge === 'end') {
        let value = gregorian(Math.round(minuteAt(c.x(item.hi) + dx)) - 1, e.precision);
        if (minuteOf(value) < item.lo) value = gregorian(item.lo, e.precision);   // not before the start
        return {[endKey(item)]: value};
      }
      let value = gregorian(Math.round(minuteAt(c.x(item.lo) + dx)), s.precision);
      if (edge === 'start') {
        if (minuteOf(value) > item.hi - 1) value = gregorian(item.hi - 1, s.precision);   // not after the end's last minute
        return {[startKey(item)]: value};
      }
      const field = {[startKey(item)]: value};
      // Shift by minutes from the start's interval, not its spelling ("April 1747" is not ISO).
      if (e) field[endKey(item)] = shiftDate(e.from, e.precision, minuteOf(value) - item.lo);
      return field;
    };
    const describe = (field) => edge === 'end' ? `ends ${dateWords(field[endKey(item)])}`
      : edge === 'start' ? `starts ${dateWords(field[startKey(item)])}` : dateWords(field[startKey(item)]);
    const tip = svgEl('text', {x: at.x, y: at.y, class: 'drag-date'}), shape = mark && {x: mark.getAttribute('x'), width: mark.getAttribute('width')};
    dragging = true; g.setPointerCapture(event.pointerId);
    const move = (ev) => {
      const dx = ev.clientX - startX;
      if (Math.abs(dx) >= DRAG_THRESHOLD) moved = true;
      if (!moved || !allowed) return;
      g.classList.add('dragging');
      if (edge === 'move') g.setAttribute('transform', `translate(${dx},0)`);
      else {
        const left = edge === 'start' ? Math.max(c.left, Math.min(bar.v1 - 2, bar.v0 + dx)) : bar.v0;
        const right = edge === 'end' ? Math.min(c.right, Math.max(bar.v0 + 2, bar.v1 + dx)) : bar.v1;
        mark.setAttribute('x', left); mark.setAttribute('width', right - left);
      }
      const text = describe(change(ev));
      tip.textContent = edge === 'move' ? text : text.charAt(0).toUpperCase() + text.slice(1);
      if (!tip.isConnected) g.append(tip);
    };
    const cleanup = () => {
      dragging = false; g.removeAttribute('transform'); g.classList.remove('dragging'); tip.remove();
      if (shape?.x != null) { mark.setAttribute('x', shape.x); mark.setAttribute('width', shape.width); }
      g.removeEventListener('pointermove', move); g.removeEventListener('pointerup', finish); g.removeEventListener('pointercancel', cleanup);
    };
    const finish = async (ev) => {
      cleanup();
      if (!moved || Math.abs(ev.clientX - startX) < DRAG_THRESHOLD) return;
      try {
        if (!await check) { toast('This date can’t be dragged. Edit it in the inspector instead.'); return; }
        if (dirty(drafts.get(item.path))) { toast('Save or discard your changes in the inspector before dragging this item.', {kind: 'error'}); return; }
        const field = change(ev), before = snapshot(item, Object.keys(field));
        if (Object.entries(field).every(([k, v]) => item.fields[k] === v)) return;
        status('Saving…', 'busy');
        const result = await api('set', {item: ref(item), field, version: item.version, expect: before});
        await refresh();
        offerUndo(item, before, field, result, edge === 'move' ? `Moved ${item.name} to ${describe(field)}.` : `${item.name} now ${describe(field)}.`);
      } catch (error) { report(error); }
    };
    g.addEventListener('pointermove', move); g.addEventListener('pointerup', finish); g.addEventListener('pointercancel', cleanup);
  });
}
function rankedPeople() {
  const counted = people().map(p => ({p, n: [...(partOf.get(p.path) || [])].filter(path => byPath.get(path)?.lo != null).length}));
  return counted.sort((a, b) => b.n - a.n || byName(a.p, b.p));
}
function peopleFilter(view, hint) {
  const bar = el('div', null, {class: 'toolbar'});
  const filter = el('input', null, {id: 'people-filter', type: 'search', placeholder: 'Filter people by name', 'aria-label': 'Filter people by name'});
  filter.value = ui.people;
  filter.addEventListener('input', () => {
    const at = filter.selectionStart;
    ui.people = filter.value; renderView();
    $('people-filter').focus(); $('people-filter').setSelectionRange(at, at);
  });
  bar.append(filter, el('span', hint, {class: 'hint'}));
  return bar;
}
function subway(view) {
  const bar = peopleFilter(view, 'Each line is a person; stops are the events they take part in.');
  bar.prepend(zoomControls());
  view.append(bar);
  const q = ui.people.toLowerCase(), ranked = rankedPeople().filter(r => r.n > 0);
  const lanes = (q ? ranked.filter(({p}) => p.name.toLowerCase().includes(q)) : ranked.slice(0, 12)).map(r => r.p);
  if (!lanes.length) {
    view.append(q ? emptyState('No one matches', `No person whose name contains “${ui.people}” takes part in a dated event.`)
      : emptyState('No journeys yet', 'Connect people to dated events with the Participants connection, and their lines appear here.'));
    return;
  }
  const box = scrollBox('chart');
  view.append(box);
  const width = Math.max(300, box.clientWidth), gutter = width < 600 ? 104 : 150, c = chart(box, width, gutter), LANE = 46, TOP = 26;
  c.svg.setAttribute('aria-label', 'Subway. Use the arrow keys to move between stops.');
  lanes.forEach((p, i) => {
    const y = TOP + i * LANE, cls = `r${i % 8}`, room = Math.floor((gutter - 20) / 7), name = p.name.length > room ? p.name.slice(0, room - 1) + '…' : p.name;
    const tag = svgEl('text', {x: 14, y: y + 4, class: `lane-name ${cls}`}, name);
    tag.append(svgEl('title', {}, p.name));
    c.svg.append(tag, svgEl('line', {x1: c.left, x2: c.right, y1: y, y2: y, class: `rail-dim ${cls}`}));
    if (p.lo != null) {
      const a = Math.max(c.left, c.x(p.lo)), b = Math.min(c.right, hasEnd(p) ? c.x(p.hi) : c.right);
      if (b > a) c.svg.append(svgEl('line', {x1: a, x2: b, y1: y, y2: y, class: `rail ${cls}`}));
    }
  });
  for (const event of events()) {
    const stops = lanes.map((p, i) => takesPart(p, event) ? i : -1).filter(i => i >= 0), x = c.x(event.lo);
    if (!stops.length || x < c.left || x > c.right) continue;
    if (stops.length > 1) c.svg.append(svgEl('line', {x1: x, x2: x, y1: TOP + stops[0] * LANE, y2: TOP + stops.at(-1) * LANE, class: 'connector'}));
    for (const lane of stops) {
      const g = svgEl('g', {class: `item r${lane % 8}`, role: 'button', tabindex: '-1', 'data-path': event.path,
        'aria-label': `${event.name}, with ${lanes[lane].name}, ${whenText(event)}`,
        id: `subway-${encodeURIComponent(`${event.path}\0${lanes[lane].path}`)}`});
      g.append(svgEl('circle', {cx: x, cy: TOP + lane * LANE, r: 11, class: 'hit'}),
        svgEl('circle', {cx: x, cy: TOP + lane * LANE, r: 6, class: 'stop'}),
        svgEl('title', {}, `${event.name} · ${whenText(event)}`));
      c.svg.append(g);
    }
  }
  c.grid(TOP + lanes.length * LANE);
  wireItems(c.svg);
  if (!q && ranked.length > lanes.length) view.append(el('p', `Showing the ${lanes.length} people with the most events. Filter to find the other ${ranked.length - lanes.length}.`, {class: 'hint'}));
}
function agesView(view) {
  view.append(peopleFilter(view, 'Ages at the events each person takes part in. Yellow: under 18. Red: before birth or after death. Who is related to whom is under Relationships.'));
  const q = ui.people.toLowerCase();
  const ranked = rankedPeople().filter(r => r.n > 0 && (!q || r.p.name.toLowerCase().includes(q))), ROWS = q ? 200 : 40;
  const shown = ranked.slice(0, ROWS).map(r => r.p).sort(byName);
  const LIMIT = 150, all = events().filter(e => shown.some(p => takesPart(p, e))), cols = all.slice(0, LIMIT);
  if (!shown.length) {
    view.append(q ? emptyState('No one matches', `No person whose name contains “${ui.people}” takes part in a dated event.`)
      : emptyState('No ages to show yet', 'Connect people to dated events with the Participants connection to see how old they are at each one.'));
    return;
  }
  const box = scrollBox('table'), table = el('table', null, {class: 'ages'}), head = el('tr'), body = el('tbody');
  table.append(el('caption', 'Age of each person at the events they take part in', {class: 'sr-only'}));
  head.append(el('th', 'Person', {scope: 'col'}));
  for (const e of cols) {
    const th = el('th', null, {scope: 'col', 'data-path': e.path, title: `${e.name} · ${whenText(e)}`});
    const name = button(e.name, () => selectItem(e.path, {show: true}), {class: 'link ev-name'});
    th.append(name, el('span', e.start.text, {class: 'ev-date'}));
    head.append(th);
  }
  add(table, el('thead')).append(head);
  table.append(body);
  const jobs = [];
  for (const p of shown) {
    const row = el('tr', null, {'data-path': p.path}), th = el('th', null, {scope: 'row'});
    th.append(button(p.name, () => selectItem(p.path, {show: true}), {class: 'link', id: `person-${encodeURIComponent(p.path)}`}));
    row.append(th);
    for (const e of cols) {
      const cell = el('td');
      if (takesPart(p, e)) {
        cell.classList.add('on');
        const key = `${p.path}|${p.version}|${e.path}|${e.version}`;
        if (p.lo == null) cell.textContent = 'No birth date';
        else if (ages.has(key)) paintAge(cell, ages.get(key));
        else {
          cell.textContent = '…';
          jobs.push(async () => {
            try { ages.set(key, await api('age', {item: ref(p), at: ref(e)})); paintAge(cell, ages.get(key)); }
            catch (error) { cell.textContent = 'Unknown'; cell.title = error.message; }
          });
        }
      }
      row.append(cell);
    }
    body.append(row);
  }
  box.append(table);
  view.append(box);
  const more = [ranked.length > shown.length && `the ${shown.length} people with the most events (of ${ranked.length})`,
    all.length > LIMIT && `the first ${LIMIT} of ${all.length} events`].filter(Boolean);
  if (more.length) view.append(el('p', `Showing ${more.join(' and ')}. Filter people to see others.`, {class: 'hint'}));
  // A small worker pool avoids flooding a large world's local server with age requests.
  for (let n = 0; n < Math.min(4, jobs.length); n++) (async () => { while (jobs.length && body.isConnected) await jobs.shift()(); })();
}
function paintAge(cell, age) {
  cell.textContent = age.text;
  cell.classList.toggle('bad', age.status !== 'alive');
  cell.classList.toggle('young', age.status === 'alive' && age.years?.[1] < 18);
}
function relationships(view) {
  // A relationship is a resolved link between two people or groups (parent, spouse, member of...);
  // events, places and timing links belong to the other views.
  view.append(peopleFilter(view, 'Who is related to whom. Add relationships in the inspector under Add a connection.'));
  const related = (i) => ['person', 'group'].includes(typeInfo(i.type).category);
  const links = graph.links.map(l => [l, byPath.get(l.from_path), byPath.get(l.to_path)])
    .filter(([l, a, b]) => l.resolved && a && b && a !== b && related(a) && related(b) && !TIMING.has(l.role));
  const cards = new Map(), own = new Set(links.map(([l, a, b]) => `${a.path}\0${l.role}\0${b.path}`));
  const put = (item, kind, other) => {
    if (!cards.has(item.path)) cards.set(item.path, new Map());
    const kinds = cards.get(item.path);
    if (!kinds.has(kind)) kinds.set(kind, new Map());
    kinds.get(kind).set(other.path, other);
  };
  for (const [l, a, b] of links) {
    put(a, label(l.role), b);
    // The other side reads the role's inverse (Children, Members), unless it states the link itself.
    if (!own.has(`${b.path}\0${l.role}\0${a.path}`)) put(b, inverseLabel(l.role), a);
  }
  const q = ui.people.toLowerCase();
  const shown = [...cards.keys()].map(path => byPath.get(path)).filter(i => !q || i.name.toLowerCase().includes(q))
    .sort((a, b) => typeRank(a.type) - typeRank(b.type) || byName(a, b));
  if (!shown.length) {
    view.append(q ? emptyState('No one matches', `No person or group whose name contains “${ui.people}” has a relationship yet.`)
      : emptyState('No relationships yet', 'Connect people with Parent, Spouse or Member of under Add a connection in the inspector, and they appear here.'));
    return;
  }
  const box = scrollBox('pad'), grid = el('div', null, {class: 'relations'});
  for (const item of shown) {
    const card = el('article', null, {class: 'relation', 'data-path': item.path}), head = el('header'), list = el('dl');
    head.append(button(item.name, () => selectItem(item.path, {show: true}), {class: 'link', id: `related-${encodeURIComponent(item.path)}`}),
      el('span', typeLabel(item.type), {class: `kind cat-${category(item)}`}));
    for (const [kind, others] of [...cards.get(item.path)].sort((a, b) => a[0].localeCompare(b[0]))) {
      const names = el('dd');
      for (const other of [...others.values()].sort(byName)) names.append(button(other.name, () => selectItem(other.path, {show: true}), {class: 'link'}));
      list.append(el('dt', kind), names);
    }
    card.append(head, list);
    grid.append(card);
  }
  box.append(grid);
  view.append(box);
}
function sortValue(item, key) {
  if (key === 'name') return item.name.toLowerCase();
  if (key === 'type') return typeLabel(item.type).toLowerCase();
  if (key === 'start') return item.lo ?? Infinity;
  if (key === 'end') return hasEnd(item) ? item.hi : Infinity;
  return display(item.fields.location).toLowerCase() || '￿';
}
function spreadsheet(view) {
  const bar = el('div', null, {class: 'toolbar'});
  const filter = el('input', null, {id: 'sheet-filter', type: 'search', placeholder: 'Filter by name', 'aria-label': 'Filter items by name'});
  filter.value = ui.sheetText;
  filter.addEventListener('input', () => {
    const at = filter.selectionStart;
    ui.sheetText = filter.value; ui.sheetLimit = 300; renderView();
    $('sheet-filter').focus(); $('sheet-filter').setSelectionRange(at, at);
  });
  const kind = el('select', null, {id: 'sheet-type', 'aria-label': 'Show one type'});
  kind.append(el('option', 'All types', {value: ''}), ...Object.keys(graph.types).sort(typeOrder).map(t => el('option', typePlural(t), {value: t})));
  kind.value = ui.sheetType;
  kind.addEventListener('change', () => { ui.sheetType = kind.value; ui.sheetLimit = 300; renderView(); });
  const q = ui.sheetText.toLowerCase(), [sortKey, dir] = ui.sort;
  const rows = graph.items.filter(i => (!ui.sheetType || i.type === ui.sheetType) && (!q || i.name.toLowerCase().includes(q)));
  rows.sort((a, b) => { const x = sortValue(a, sortKey), y = sortValue(b, sortKey); return (x < y ? -1 : x > y ? 1 : byName(a, b)) * dir; });
  bar.append(filter, kind, el('span', `${plural(rows.length, 'item')}${rows.length < graph.items.length ? ` of ${graph.items.length}` : ''}`, {class: 'hint', 'aria-live': 'polite'}),
    el('span', null, {class: 'spacer'}), el('span', saga ? 'Select a row to propose changes in the inspector.' : 'Enter or leaving a cell saves it. Esc undoes your typing.', {class: 'hint'}));
  view.append(bar);
  const box = scrollBox('table'), table = el('table', null, {class: 'sheet'}), head = el('tr'), body = el('tbody');
  table.append(el('caption', 'All items', {class: 'sr-only'}));
  for (const [key, text] of [['name', 'Name'], ['type', 'Type'], ['start', 'Date or born'], ['end', 'End or died'], ['location', 'Location']]) {
    const th = el('th', null, {scope: 'col', 'aria-sort': sortKey === key ? (dir > 0 ? 'ascending' : 'descending') : 'none'});
    th.append(button(text, () => { ui.sort = [key, sortKey === key ? -dir : 1]; renderView(); }, {id: `sort-${key}`}));
    head.append(th);
  }
  add(head, el('th', null, {scope: 'col'})).append(el('span', 'Open', {class: 'sr-only'}));
  add(table, el('thead')).append(head);
  table.append(body);
  const allowed = graph.roles.location?.to || [], places = new Map(), placeList = el('datalist', null, {id: 'sheet-places'});
  for (const place of graph.items.filter(i => !allowed.length || allowed.includes(i.type)).sort(byName)) {
    if (places.has(place.name.toLowerCase())) continue;
    places.set(place.name.toLowerCase(), place);
    placeList.append(el('option', null, {value: place.name}));
  }
  // ponytail: rows render in pages of 300; virtualise if a world needs to scroll tens of thousands.
  for (const item of rows.slice(0, ui.sheetLimit)) {
    const row = el('tr', null, {'data-path': item.path});
    row.append(sheetCell(item, nameKey(item)), sheetType(item), sheetCell(item, startKey(item)), sheetCell(item, endKey(item)), sheetLocation(item, places));
    const open = el('td', null, {class: 'open'});
    open.append(button('Open', () => selectItem(item.path, {focus: 'title', show: true}), {class: 'quiet', id: `inspect-${encodeURIComponent(item.path)}`, 'aria-label': `Open ${item.name}`}));
    row.append(open);
    body.append(row);
  }
  box.append(table);
  view.append(box);
  box.append(placeList);
  if (rows.length > ui.sheetLimit) box.append(button(`Show ${Math.min(300, rows.length - ui.sheetLimit)} more of ${rows.length - ui.sheetLimit} not shown`,
    () => { ui.sheetLimit += 300; renderView(); }, {class: 'quiet', id: 'sheet-more'}));
  if (!rows.length) view.append(el('p', 'No items match this filter.', {class: 'hint'}));
}
// A cell draft is {base: the item as it was when typing began, value: the text}; base guards the save.
async function saveCell(id, input, draft, key, value) {
  const item = draft.base, sent = draft.value, field = {}, unset = [], original = item.fields[key];
  input.classList.remove('failed', 'saved');
  if ((value === '' || value == null) && key === nameKey(item)) {
    input.classList.add('failed');
    report(new ApiError('INVALID', 'An item needs a name. Type one, or press Esc to put the old name back.'));
    return;
  }
  if (value === '' || value == null) { if (original === undefined) { cells.delete(id); idle(); return; } unset.push(key); }
  else field[key] = value;
  status('Saving…', 'busy');
  try {
    const result = await api('set', {item: ref(item), field, unset, version: item.version, expect: {[key]: original ?? null}});
    // Text typed while this save was in flight is a newer draft: keep it, based on what was just saved.
    if (cells.get(id) === draft) {
      if (draft.value === sent) cells.delete(id);
      else {
        const fields = {...item.fields, ...field};
        for (const k of unset) delete fields[k];
        draft.base = {...item, version: result.version, fields};
      }
    }
    ui.flash = {id, until: Date.now() + 1600};
    input.classList.add('saved');
    setTimeout(() => input.classList.remove('saved'), 1600);
    refresh().then(idle, error => report(error, [], 'Could not reload'));
  } catch (error) {
    input.classList.add('failed');
    report(error, error.data?.current ? [['Load their version', async () => { cells.delete(id); await refresh(); idle(); }]] : []);
  }
}
function cellId(item, key) { return `cell-${encodeURIComponent(`${item.path}\0${key}`)}`; }
function wireCell(input, item, key) {
  const id = cellId(item, key);
  if (ui.flash?.id === id && Date.now() < ui.flash.until) input.classList.add('saved');
  input.addEventListener('focus', () => { if (selected !== item.path) selectItem(item.path); });
  return id;
}
// The sheet is not redrawn while a cell has focus, so cells read the latest copy of their item.
const latestOf = (item) => byPath.get(item.path) || item;
function editableCell(input, item, key, {shown, toValue}) {
  const id = wireCell(input, item, key), draft = cells.get(id);
  input.id = id;
  input.value = draft?.value ?? shown();
  input.readOnly = saga;
  if (draft?.failed) input.classList.add('failed');
  input.addEventListener('input', () => {
    const d = cells.get(id);
    if (d) d.value = input.value; else cells.set(id, {base: latestOf(item), value: input.value});
    idle();
  });
  const save = () => {
    const d = cells.get(id);
    if (!d) return;
    if (d.saving) { d.again = true; return; }   // Enter or leaving the cell mid-save: save the newer text next
    if (d.value.trim() === shown()) { cells.delete(id); input.classList.remove('failed'); idle(); return; }
    const value = toValue(d);
    if (value === undefined) { input.classList.add('failed'); d.failed = true; return; }
    d.saving = true;
    saveCell(id, input, d, key, value).finally(() => {
      d.saving = false; d.failed = input.classList.contains('failed');
      if (d.again && !d.failed) { d.again = false; save(); }
    });
  };
  input.addEventListener('blur', save);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); save(); }
    if (event.key === 'Escape') { cells.delete(id); input.value = shown(); input.classList.remove('failed'); idle(); }
  });
  return input;
}
function sheetCell(item, key) {
  const cell = el('td'), input = el('input', null, {'aria-label': `${item.name}: ${label(key)}`, autocomplete: 'off'});
  cell.append(editableCell(input, item, key, {shown: () => display(latestOf(item).fields[key]),
    toValue: (d) => valueOf(d.value, d.base.fields[key], key)}));
  return cell;
}
function sheetType(item) {
  const cell = el('td'), select = el('select', null, {'aria-label': `${item.name}: Type`});
  select.id = wireCell(select, item, 'type');
  for (const type of Object.keys(graph.types).sort(typeOrder)) select.append(el('option', typeLabel(type), {value: type}));
  if (!graph.types[item.type]) select.append(el('option', item.type, {value: item.type}));
  select.value = item.type;
  select.disabled = saga;
  select.addEventListener('change', () => saveCell(select.id, select, {base: latestOf(item), value: select.value}, 'type', select.value));
  cell.append(select);
  return cell;
}
function sheetLocation(item, places) {
  // One shared list of places for every row: a select per row would repeat it thousands of times.
  if (!isRole('location')) return sheetCell(item, 'location');
  const shown = () => {
    const link = graph.links.find(l => l.from_path === item.path && l.role === 'location');
    return link ? (byPath.get(link.to_path)?.name || link.to) : '';
  };
  const cell = el('td'), input = el('input', null, {list: 'sheet-places', 'aria-label': `${item.name}: Location`, autocomplete: 'off'});
  cell.append(editableCell(input, item, 'location', {shown, toValue: (d) => {
    const text = d.value.trim(), place = places.get(text.toLowerCase());
    if (!text) return '';
    if (place) return `[[${place.name}]]`;
    report(new ApiError('INVALID', `There is no place called “${text}”. Choose one from the list, or press Esc.`));
    return undefined;
  }}));
  return cell;
}
function narrative(view) {
  // Hosts' cards use chapter/order/number; natural name order is the fallback.
  const order = (i) => Number(i.fields.chapter ?? i.fields.order ?? i.fields.number ?? i.name.match(/\d+/)?.[0] ?? Infinity);
  const chapters = graph.items.filter(i => category(i) === 'narrative' || i.type === 'card')
    .sort((a, b) => order(a) - order(b) || byName(a, b));
  if (!chapters.length) {
    view.append(emptyState('No chapters yet', 'Chapters and other story parts appear here in reading order, with a flag wherever the story steps back in time.',
      saga || !graph.types.chapter ? null : ['Create a chapter', () => openCreate('chapter')]));
    return;
  }
  const kinds = new Set(chapters.map(c => c.type)).size > 1, box = scrollBox('pad'), list = el('ol', null, {class: 'cards'});
  let latest = null;
  chapters.forEach((item, index) => {
    const row = el('li', null, {'data-path': item.path}), main = el('div');
    main.append(button(item.name, () => selectItem(item.path, {show: true}), {class: 'link', id: `narrative-${encodeURIComponent(item.path)}`}),
      el('div', `${kinds ? typeLabel(item.type) + (item.start ? ' · ' : '') : ''}${item.start ? whenText(item) : ''}`, {class: 'when'}));
    const back = latest != null && item.lo != null && item.lo < latest;
    row.append(el('span', String(index + 1), {class: 'num'}), main,
      back ? el('span', 'Earlier than the part before', {class: 'flag warn', title: 'The story steps back in time here. A flashback may be intentional.'})
        : item.lo == null ? el('span', 'Undated', {class: 'flag muted'}) : el('span'));
    if (item.lo != null) latest = Math.max(latest ?? item.lo, item.lo);
    list.append(row);
  });
  box.append(list);
  view.append(el('p', 'Story parts in reading order, by their chapter, order or number field.', {class: 'hint'}), box);
}
async function runCheck() {
  if (ui.checking) { ui.recheck = true; return; }
  ui.checking = true;
  if (tab === 'Continuity') renderView();
  try { ui.findings = await api('check'); ui.checkError = null; ui.checkedAt = new Date(); }
  catch (error) { ui.checkError = error; }
  finally {
    ui.checking = false;
    updateBadge();
    if (tab === 'Continuity') renderView();
    if (ui.recheck) { ui.recheck = false; runCheck(); }
  }
}
function scheduleCheck() { clearTimeout(checkTimer); checkTimer = setTimeout(runCheck, 500); }
function updateBadge() {
  const badge = $('check-badge'), result = ui.findings, tabNode = $('tab-continuity');
  if (!result) { badge.hidden = true; return; }
  badge.hidden = !result.fail && !result.warn;
  badge.textContent = String(result.fail || result.warn);
  badge.className = `badge ${result.fail ? 'fail' : 'warn'}`;
  tabNode.setAttribute('aria-label', `Continuity: ${plural(result.fail, 'definite problem')}, ${plural(result.warn, 'possible problem')}`);
}
function continuity(view) {
  const bar = el('div', null, {class: 'toolbar'});
  bar.append(button('Check again', runCheck, {id: 'check-again'}),
    el('span', ui.checking ? 'Checking…' : ui.checkedAt ? `Checked at ${ui.checkedAt.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}` : '', {class: 'hint'}));
  view.append(bar);
  if (ui.checkError) { view.append(emptyState('The check could not run', explain(ui.checkError))); return; }
  const result = ui.findings;
  if (!result) { view.append(emptyState('Checking your world…', 'Lorekeeper is comparing dates, ages, deaths, places and links.')); return; }
  if (!result.findings.length) {
    view.append(emptyState('No continuity problems found', `Lorekeeper checked ${plural(graph.items.length, 'item')}: dates, ages, deaths, places and links all agree.`));
    return;
  }
  const summary = el('div', null, {class: 'summary'});
  summary.append(el('strong', `${plural(result.fail, 'definite problem')}, ${plural(result.warn, 'possible one')}`),
    el('span', 'Definite problems contradict your dates. Possible ones depend on uncertain or missing information. Lorekeeper never changes your files to fix them.', {class: 'hint'}));
  view.append(summary);
  const box = scrollBox('pad');
  for (const [severity, title] of [['FAIL', 'Definite problems'], ['WARN', 'Possible problems']]) {
    const found = result.findings.filter(f => f.severity === severity);
    if (!found.length) continue;
    box.append(el('h3', `${title} · ${found.length}`, {class: 'section-title'}));
    const list = el('ol', null, {class: 'cards findings'});
    const LIMIT = 150;
    for (const f of ui.allFindings ? found : found.slice(0, LIMIT)) {
      const row = el('li', null, f.path && byPath.has(f.path) ? {'data-path': f.path} : {});
      const item = byPath.get(f.path), where = el('div', null, {class: 'where'});
      if (item) where.append(button(`Open ${item.name}`, () => selectItem(item.path, {reveal: true, focus: 'title'}), {class: 'link'}));
      where.append(el('span', `${f.path}${f.line ? `:${f.line}` : ''}`, {class: 'path'}));
      row.append(el('span', severity === 'FAIL' ? 'Definite' : 'Possible', {class: `flag ${severity === 'FAIL' ? 'fail' : 'warn'}`}),
        el('strong', TITLES[f.code] || words(f.code.toLowerCase())), el('span', f.detail, {class: 'detail'}), where);
      list.append(row);
    }
    box.append(list);
    if (!ui.allFindings && found.length > LIMIT) box.append(button(`Show all ${found.length}`, () => { ui.allFindings = true; renderView(); }, {class: 'quiet'}));
  }
  view.append(box);
}
// ---- story wiki: what the reader knows by a chapter ------------------------------------------
// Page text is drawn as DOM text nodes (never innerHTML): a small Markdown subset, links as buttons.
const AS_OF_KEY = 'lore-wiki-as-of';
const wiki = {asOf: null, filter: '', open: null, openName: '', cardAsOf: null, index: null, card: null,
  cardError: null, error: null, loaded: null, loading: null, form: null};
try { const kept = localStorage.getItem(AS_OF_KEY); if (/^\d+$/.test(kept || '')) wiki.asOf = Number(kept); } catch { /* private window */ }
const chText = (from, to) => from == null ? '' : to == null ? `ch ${from}` : `ch ${from}–${to}`;
// "Chapter 003 — First Boots" reads "Chapter 3 — First Boots"; a bare "Chapter 3" adds nothing.
const chapterName = (c) => {
  const rest = (c.name || '').trim().replace(new RegExp(`^(chapter|ch)\\s*0*${c.n}\\b\\s*[—–:.-]*\\s*`, 'i'), '');
  return rest ? `Chapter ${c.n} — ${rest}` : `Chapter ${c.n}`;
};
const lastChapter = () => wiki.index?.chapters.at(-1)?.n ?? 1;
function inline(parent, text) {
  // **bold**, *italic*, [[Link]] and [[Link|label]]; everything else stays plain text.
  for (const part of String(text).split(/(\[\[[^\[\]\n]+\]\]|\*\*[^*\n]+\*\*|\*[^*\s][^*\n]*\*)/)) {
    if (!part) continue;
    const link = part.match(/^\[\[([^\]|]+)(?:\|([^\]]*))?\]\]$/);
    if (link) parent.append(button(link[2] || link[1], () => openEntry(link[1].split('#')[0].trim(), link[2] || link[1]), {class: 'link'}));
    else if (/^\*\*.+\*\*$/.test(part)) parent.append(el('strong', part.slice(2, -2)));
    else if (/^\*.+\*$/.test(part)) parent.append(el('em', part.slice(1, -1)));
    else part.split('\n').forEach((line, i) => { if (i) parent.append(el('br')); parent.append(line); });
  }
  return parent;
}
function markdown(text) {
  const box = el('div', null, {class: 'md'});
  let list = null, para = null;
  for (const raw of String(text).split(/\r?\n/)) {
    const line = raw.trimEnd(), heading = line.match(/^(#{1,6})\s+(.*)$/), item = line.match(/^\s*(?:[-*+]|\d+[.)])\s+(.*)$/);
    if (!line.trim() || heading) { list = para = null; }
    if (heading) { if (heading[1].length > 1) box.append(el('h4', heading[2].replace(/#+$/, '').trim())); continue; }
    if (item) { para = null; list ||= add(box, el('ul')); inline(add(list, el('li')), item[1]); continue; }
    if (!line.trim()) continue;
    if (para) { para.append(el('br')); inline(para, line.trim()); } else { list = null; para = inline(add(box, el('p')), line.trim()); }
  }
  return box;
}
async function wikiLoad() {
  const want = JSON.stringify([lastStamp, wiki.asOf, wiki.open, wiki.cardAsOf]);
  if (wiki.loaded === want || wiki.loading === want) return;
  wiki.loading = want;
  try {
    const index = await api('wiki', wiki.asOf == null ? {} : {as_of: wiki.asOf});
    let card = null, cardError = null;
    if (wiki.open) {
      try { card = await api('wiki', {item: wiki.open, ...(wiki.cardAsOf == null ? {} : {as_of: wiki.cardAsOf})}); }
      catch (error) { if (error.code !== 'NOT_FOUND') throw error; cardError = error; }
    }
    if (wiki.loading !== want) return;   // a newer request is on its way: never show this older answer
    Object.assign(wiki, {index, card, cardError, error: null});
    // The inspector follows the open card in Complete; at a chapter it is cleared, since its fields would give later facts away.
    const follow = card?.page && byPath.has(card.page) ? card.page : wiki.open ? '' : selected;
    if (follow !== selected && tab === 'Wiki') { selected = follow; renderInspector(); }
  } catch (error) { if (wiki.loading !== want) return; wiki.error = error; }
  wiki.loading = null; wiki.loaded = want;
  if (tab === 'Wiki') renderView();
}
function openEntry(key, name, fromIndex = false) {
  // From the index a card starts at the picker's chapter; a link inside a card keeps that card's chapter.
  Object.assign(wiki, {open: key, openName: name, cardAsOf: fromIndex || !wiki.open ? wiki.asOf : wiki.cardAsOf, form: null});
  if (wiki.open !== wiki.card?.key) wiki.card = null;
  renderView();
  requestAnimationFrame(() => $('wiki-title')?.focus({preventScroll: true}));
}
function setCardChapter(value) { wiki.cardAsOf = value; wiki.form = null; renderView(); }
function chapterSelect(id, value, onChange, labelText) {
  const select = el('select', null, {id, 'aria-label': labelText});
  select.append(el('option', 'Complete', {value: ''}));
  for (const c of wiki.index?.chapters || []) select.append(el('option', chapterName(c), {value: String(c.n)}));
  select.value = value == null ? '' : String(value);
  select.addEventListener('change', () => onChange(select.value === '' ? null : Number(select.value)));
  return select;
}
function wikiView(view) {
  wikiLoad();
  const bar = el('div', null, {class: 'toolbar'}), filter = el('input', null, {id: 'wiki-filter', type: 'search', placeholder: 'Filter entries', 'aria-label': 'Filter wiki entries', autocomplete: 'off'});
  filter.value = wiki.filter;
  filter.addEventListener('input', () => { wiki.filter = filter.value; $('view').querySelector('.wiki-index')?.replaceWith(wikiIndex()); });
  const picker = chapterSelect('wiki-as-of', wiki.asOf, (value) => {
    wiki.asOf = value; wiki.cardAsOf = value; wiki.form = null;
    try { value == null ? localStorage.removeItem(AS_OF_KEY) : localStorage.setItem(AS_OF_KEY, String(value)); } catch { /* not kept */ }
    renderView();
  }, 'Show the wiki as of');
  const label = el('label', null, {for: 'wiki-as-of'});
  label.append('Wiki as of ', picker);
  bar.append(label, filter, el('span', wiki.asOf == null ? 'Everything, for the author.' : `Only what a reader knows after chapter ${wiki.asOf}.`, {class: 'hint'}));
  view.append(bar);
  if (wiki.error) { view.append(emptyState('The wiki could not load', explain(wiki.error))); return; }
  if (!wiki.index) { view.append(emptyState('Opening the wiki…', 'Lorekeeper is reading the story pages.')); return; }
  const layout = el('div', null, {class: 'wiki'});
  layout.append(wikiIndex(), wikiCard());
  view.append(layout);
}
function wikiIndex() {
  const list = el('nav', null, {class: 'scroll pad wiki-index', 'data-tab': 'Wiki', 'aria-label': 'Wiki entries'});
  const q = wiki.filter.trim().toLowerCase();
  let shown = 0;
  for (const group of wiki.index.groups) {
    const entries = group.entries.filter(e => !q || [e.name, ...e.also].some(n => n.toLowerCase().includes(q)));
    if (!entries.length) continue;
    shown += entries.length;
    list.append(el('h3', `${group.label} · ${entries.length}`, {class: 'section-title'}));
    const ul = add(list, el('ul', null, {class: 'wiki-list'}));
    for (const e of entries) {
      const li = add(ul, el('li'));
      li.append(button(e.name, () => openEntry(e.key, e.name, true), {class: 'wiki-entry', id: `wiki-${encodeURIComponent(e.key)}`,
        'aria-current': wiki.card?.key === e.key || wiki.open === e.key ? 'true' : null}));
      if (e.also.length) li.append(el('span', `also ${e.also.join(', ')}`, {class: 'hint'}));
    }
  }
  if (!shown) list.append(el('p', q ? `No entry matches “${wiki.filter}”.` : wiki.asOf == null ? 'No entries yet.' : `The reader has met no one yet by chapter ${wiki.asOf}.`, {class: 'hint'}));
  return list;
}
function wikiCard() {
  const box = el('article', null, {class: 'scroll pad wiki-card', 'aria-labelledby': 'wiki-title'});
  if (!wiki.open) {
    box.append(emptyState('Pick an entry', wiki.asOf == null ? 'Each card holds everything known about one character, place, group or thing.'
      : `Each card shows only what the reader knows after chapter ${wiki.asOf}. Change a card’s own chapter at its top.`));
    return box;
  }
  const card = wiki.card;
  const head = el('header', null, {class: 'wiki-head'}), title = el('div');
  title.append(el('h2', card?.name || wiki.openName, {id: 'wiki-title', tabindex: '-1'}));
  const toggle = el('div', null, {class: 'card-toggle', role: 'group', 'aria-label': 'Chapter for this card'});
  const chapters = (wiki.index.chapters || []).map(c => c.n), at = chapters.indexOf(wiki.cardAsOf);
  const step = (delta) => {
    if (wiki.cardAsOf == null) return setCardChapter(delta < 0 ? chapters.at(-1) ?? null : null);
    const next = chapters[at + delta];
    setCardChapter(next === undefined ? (delta > 0 ? null : wiki.cardAsOf) : next);
  };
  toggle.append(button([icon('left')], () => step(-1), {class: 'quiet icon-only', 'aria-label': 'Previous chapter', id: 'card-prev', disabled: at === 0 ? '' : null}),
    chapterSelect('card-as-of', wiki.cardAsOf, setCardChapter, 'Show this card as of'),
    button([icon('right')], () => step(1), {class: 'quiet icon-only', 'aria-label': 'Next chapter', id: 'card-next', disabled: wiki.cardAsOf == null ? '' : null}));
  head.append(title, toggle);
  box.append(head);
  if (wiki.cardError) {
    box.append(el('p', wiki.cardAsOf == null ? `There is no entry named ${wiki.openName} any more.`
      : `The reader does not know ${wiki.openName} by that name at chapter ${wiki.cardAsOf}. Choose a later chapter or Complete.`, {class: 'hint'}));
    return box;
  }
  if (!card) { box.append(el('p', 'Opening…', {class: 'hint'})); return box; }
  const meta = el('p', null, {class: 'meta'});
  meta.append(el('span', typeLabel(card.type), {class: `kind cat-${CATEGORIES.includes(typeInfo(card.type).category) ? typeInfo(card.type).category : 'other'}`}));
  if (card.appears != null) meta.append(el('span', `Appears in chapter ${card.appears}`));
  if (card.also.length) meta.append(el('span', `Also ${card.also.join(', ')}`));
  title.append(meta);
  if (card.opened) title.append(el('p', `${card.opened} is ${card.name}${wiki.cardAsOf == null ? '' : ` (revealed by chapter ${wiki.cardAsOf})`}.`, {class: 'hint'}));
  if (card.names.length) {
    title.append(el('p', `${wiki.cardAsOf == null ? 'Names' : 'Also known as'}: ${card.names.map(n => `${n.name}${n.from != null ? ` (${chText(n.from, n.to)})` : ''}`).join(', ')}`, {class: 'hint'}));
  }
  if (card.page) {
    const item = byPath.get(card.page);
    if (item) head.append(button('Edit', () => selectItem(item.path, {show: true, focus: 'title'}), {class: 'quiet edit-entry'}));
  }
  if (card.body?.trim()) {
    const page = add(box, el('details', null, {class: 'working', open: ''}));
    page.append(el('summary', 'From the page (written for the present)'), markdown(card.body));
  }
  // Empty sections (a new story page's starter headings) stay out of sight; "another section" offers them.
  const sections = card.sections.filter(s => s.facts.length);
  if (!sections.length) box.append(el('p', wiki.cardAsOf == null ? 'No story facts are recorded yet.' : `Nothing known yet about ${card.name} at this chapter.`, {class: 'hint'}));
  sections.forEach((section, index) => box.append(wikiSection(card, section, index)));
  if (!saga || !card.standalone) {
    const other = add(box, el('section', null, {class: 'wiki-section'}));
    if (wiki.form === 'other') other.append(addForm(card, null, 'other'));
    else other.append(button([icon('plus'), sections.length ? 'Add a fact to another section' : 'Add the first fact'],
      () => { wiki.form = 'other'; renderView(); requestAnimationFrame(() => $('wiki-form-section')?.focus()); }, {class: 'quiet small', id: 'wiki-add-other'}));
  }
  if (card.fields) {
    const fields = Object.entries(card.fields).filter(([k]) => !['id', 'type', 'canonical_name', 'name', 'page'].includes(k));
    if (fields.length) {
      const facts = add(box, el('section', null, {class: 'wiki-section'})), dl = el('dl', null, {class: 'wiki-fields'});
      facts.append(el('h3', 'Fields'), dl);
      for (const [key, value] of fields) { dl.append(el('dt', label(key))); inline(add(dl, el('dd')), display(value).replace(/\n/g, ', ')); }
    }
  }
  return box;
}
function wikiSection(card, section, index) {
  const box = el('section', null, {class: 'wiki-section'}), id = `wiki-sec-${index}`;
  box.append(el('h3', section.heading || 'Overview', {id}));
  const complete = wiki.cardAsOf == null;
  if (section.facts.length) {
    const ul = add(box, el('ul', null, {class: 'facts', 'aria-labelledby': id}));
    section.facts.forEach((fact, n) => {
      const li = add(ul, el('li', null, {class: `fact${complete && fact.to != null ? ' ended' : ''}`}));
      inline(add(li, el('span', null, {class: 'text'})), fact.text);
      const marks = add(li, el('span', null, {class: 'marks'}));
      if (fact.from != null) marks.append(el('span', chText(fact.from, fact.to), {class: 'ch', title: fact.to == null ? `Known from chapter ${fact.from}` : `True from chapter ${fact.from} to ${fact.to}`}));
      if (complete && fact.to != null) marks.append(el('span', 'no longer current', {class: 'tag'}));
      if (fact.as) marks.append(el('span', `as ${fact.as}`, {class: 'tag'}));
      if (fact.worked_out) marks.append(el('span', 'worked out', {class: 'tag', title: 'Filled in from links between items; nothing is written here yet.'}));
      if (!fact.worked_out && fact.to == null) {
        const formId = `${index}:${n}:end`;
        if (wiki.form === formId) li.append(endForm(card, section, fact, formId));
        else marks.append(button(saga ? 'Propose an end' : 'No longer true after…', () => { wiki.form = formId; renderView(); requestAnimationFrame(() => $('wiki-form-input')?.focus()); },
          {class: 'quiet small', id: `wiki-end-${index}-${n}`}));
      }
    });
  } else box.append(el('p', wiki.cardAsOf == null ? 'Nothing recorded yet.' : 'Nothing known yet at this chapter.', {class: 'hint'}));
  const formId = `${index}:add`;
  if (saga && card.standalone) box.append(el('p', 'Add facts for this entry with fact-add.', {class: 'hint'}));
  else if (!section.heading) { /* the untitled opening: new facts go under a heading ("another section") */ }
  else if (wiki.form === formId) box.append(addForm(card, section, formId));
  else box.append(button([icon('plus'), saga ? 'Propose a fact' : 'Add a fact'], () => { wiki.form = formId; renderView(); requestAnimationFrame(() => $('wiki-form-input')?.focus()); },
    {class: 'quiet small', 'aria-describedby': id, id: `wiki-add-${index}`}));
  return box;
}
function wikiForm(fields, submitText, onSubmit, returnId) {
  // After saving or cancelling, focus goes back to the control that opened the form (or the card title).
  const done = () => { wiki.form = null; renderView(); requestAnimationFrame(() => ($(returnId) || $('wiki-title'))?.focus({preventScroll: true})); };
  const form = el('form', null, {class: 'wiki-form'});
  form.append(...fields, el('div', null, {class: 'row'}));
  const row = form.lastChild;
  row.append(el('button', submitText, {type: 'submit', class: 'primary'}), button('Cancel', done, {class: 'quiet'}));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    try { await onSubmit(); done(); } catch (error) { report(error, error.code === 'CONFLICT' ? [['Reload the card', () => refresh()]] : []); }
    finally { submit.disabled = false; }
  });
  form.addEventListener('keydown', event => { if (event.key === 'Escape') { event.stopPropagation(); done(); } });
  return form;
}
function numberField(id, text, value) {
  const wrap = el('label', null, {for: id, class: 'chapter-field'}), input = el('input', null, {id, type: 'number', min: '0', step: '1', required: '', inputmode: 'numeric'});
  input.value = String(value);
  wrap.append(text, input);
  return [wrap, input];
}
function addForm(card, section, formId) {
  // section null: the writer names the section; the type's starter sections are offered.
  const fields = [];
  let sectionInput = null;
  if (!section) {
    const wrap = el('label', null, {for: 'wiki-form-section', class: 'chapter-field'}), list = el('datalist', null, {id: 'wiki-sections'});
    sectionInput = el('input', null, {id: 'wiki-form-section', list: 'wiki-sections', required: '', autocomplete: 'off', placeholder: 'e.g. Wants'});
    for (const h of typeInfo(card.type).sections || []) if (!card.sections.some(s => s.facts.length && s.heading.toLowerCase() === h.toLowerCase())) list.append(el('option', null, {value: h}));
    wrap.append('Section ', sectionInput, list);
    fields.push(wrap);
  }
  const text = el('input', null, {id: section ? 'wiki-form-input' : 'wiki-form-text', required: '', autocomplete: 'off', 'aria-label': section ? `New fact in ${section.heading || 'Overview'}` : 'New fact', placeholder: 'One fact, e.g. Lost his left hand at the Gate.'});
  const [from, fromInput] = numberField('wiki-form-from', 'Known from chapter ', wiki.cardAsOf ?? lastChapter());
  return wikiForm([...fields, text, from], saga ? 'Propose' : 'Add', async () => {
    const fact = text.value.trim(), start = Number(fromInput.value), heading = section ? section.heading || 'Overview' : sectionInput.value.trim();
    if (!heading) { sectionInput.focus(); throw new ApiError('INVALID', 'Name the section first, for example Wants.'); }
    if (!fact) { text.focus(); throw new ApiError('INVALID', 'Write the fact first.'); }
    if (saga) {
      await api('request', {item: card.key, note: `Story Wiki: add to ${card.name} › ${heading}: "${fact}" [ch ${start}]`});
      toast(`Fact for ${card.name} proposed. The story files stay as they are until the pipeline applies it.`);
      renderView();
      return;
    }
    const result = await api('fact-add', {item: card.key, section: heading, text: fact, from: start, ...(card.version ? {version: card.version} : {})});
    await refresh();
    toast(`Added to ${card.name} › ${heading}.`, {actions: [['Undo', async () => {
      await api('fact-remove', {item: card.key, section: heading, fact: result.id, version: result.version});
      await refresh();
      toast('Undone.');
    }]]});
  }, section ? `wiki-add-${formId.split(':')[0]}` : 'wiki-add-other');
}
function endForm(card, section, fact, formId) {
  const [after, afterInput] = numberField('wiki-form-input', 'No longer true after chapter ', Math.max(fact.from ?? 0, wiki.cardAsOf ?? lastChapter()));
  // The fact's id names exactly this fact (folded facts live on the folded page: fact.key).
  const key = fact.key || card.key, heading = section.heading || '(untitled)';
  const words = fact.text.replace(/\[\[([^\]|]+)(?:\|([^\]]*))?\]\]/g, (m, a, b) => b || a);
  return wikiForm([after], saga ? 'Propose' : 'Save', async () => {
    const end = Number(afterInput.value);
    if (saga) {
      await api('request', {item: card.key, note: `Story Wiki: in ${card.name} › ${heading}, "${words}" is no longer true after chapter ${end}`});
      toast(`End proposed for ${card.name}. The story files stay as they are until the pipeline applies it.`);
      renderView();
      return;
    }
    const result = await api('fact-end', {item: key, section: heading, fact: fact.id, after: end, ...(!fact.key && card.version ? {version: card.version} : {})});
    await refresh();
    toast(`Marked as no longer true after chapter ${end}.`, {actions: [['Undo', async () => {
      await api('fact-end', {item: key, section: heading, fact: result.id, reopen: true, version: result.version});
      await refresh();
      toast('Undone.');
    }]]});
  }, 'wiki-title');
}
const VIEWS = {Timeline: timeline, Subway: subway, Relationships: relationships, Ages: agesView, Spreadsheet: spreadsheet, Narrative: narrative, Wiki: wikiView, Continuity: continuity};
function rememberScroll() {
  const box = $('view').querySelector('.scroll');
  if (box) scrolls.set(box.dataset.tab, [box.scrollTop, box.scrollLeft]);
}
function renderView() {
  const view = $('view'), focusId = view.contains(document.activeElement) ? document.activeElement.id : null;
  rememberScroll();
  view.replaceChildren();
  if (!graph.items.length && tab !== 'Continuity') view.append(welcome());
  else VIEWS[tab](view);
  const box = view.querySelector('.scroll'), memory = box && scrolls.get(box.dataset.tab);
  if (memory) [box.scrollTop, box.scrollLeft] = memory;
  markSelection();
  if (focusId) $(focusId)?.focus({preventScroll: true});
}
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => { renderPending = false; renderView(); });
}

// ---- loading and live reload ----------------------------------------------------------------
function indexGraph() {
  graph.properties ||= {};
  byPath = new Map(graph.items.map(i => [i.path, i]));
  partOf = new Map();
  for (const link of graph.links) {
    if (link.role !== 'participants' || !link.resolved) continue;
    if (!partOf.has(link.to_path)) partOf.set(link.to_path, new Set());
    partOf.get(link.to_path).add(link.from_path);
  }
}
function refresh() {
  // A mutation's reload must run after any poll already in flight, not be skipped.
  const pending = refreshQueue.then(loadGraph);
  refreshQueue = pending.catch(() => {});
  return pending;
}
async function loadGraph() {
  refreshing = true;
  try {
    // Stamp before graph: a concurrent file edit during graph loading is caught on the next poll.
    const stampResponse = await fetch('/api/stamp');
    if (!stampResponse.ok) throw new ApiError('IO_ERROR', 'Could not read the project stamp.');
    const stamp = (await stampResponse.json()).stamp;
    graph = await api('graph');
    lastStamp = stamp;
    indexGraph(); renderFind(); renderCreateTypes();
    $('world').textContent = `${worldName} · ${plural(graph.items.length, 'item')}`;
    const active = document.activeElement;
    if (!($('view').contains(active) && typing(active)) && !dragging) renderView();
    if (!$('inspector').contains(active)) renderInspector();
    scheduleCheck();
  } finally { refreshing = false; }
}

const tabs = [...document.querySelectorAll('[role="tab"]')];
function activateTab(node) {
  rememberScroll();
  tab = node.dataset.view;
  tabs.forEach(t => { t.setAttribute('aria-selected', String(t === node)); t.tabIndex = t === node ? 0 : -1; });
  $('view').setAttribute('aria-labelledby', node.id);
  renderView();
  if (tab === 'Continuity' && !ui.checking) runCheck();
}
tabs.forEach((node, index) => {
  node.addEventListener('click', () => activateTab(node));
  node.addEventListener('keydown', event => {
    const next = {ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1}[event.key];
    if (next != null) { event.preventDefault(); tabs[next].focus(); activateTab(tabs[next]); }
  });
});
$('find').addEventListener('input', () => { if (findPaths.has($('find').value)) pickFind(false); });
$('find').addEventListener('keydown', event => {
  if (event.key === 'Enter') { event.preventDefault(); pickFind(true); }
  if (event.key === 'Escape') { $('find').value = ''; $('find').blur(); }
});
$('create-form').addEventListener('submit', async event => {
  event.preventDefault();
  const submit = event.target.querySelector('button'), name = $('create-name').value.trim();
  if (!name) { $('create-name').focus(); return; }
  submit.disabled = true;
  try {
    const item = await api('create', {type: $('create-type').value, name});
    $('create-name').value = ''; $('new-item').open = false;
    await refresh();
    selectItem(item.path, {reveal: true});
    const created = byPath.get(item.path);
    (created && $(`field-${startKey(created)}`) || $('inspector-title'))?.focus();
    toast(`Created ${name}. Add a date and connections in the inspector.`);
  } catch (error) { report(error, [], 'Not created'); }
  finally { submit.disabled = false; }
});
document.addEventListener('click', event => {
  for (const node of document.querySelectorAll('details.new-item[open], details.shortcuts[open]')) if (!node.contains(event.target)) node.open = false;
});
document.addEventListener('keydown', event => {
  const target = event.target;
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault();
    if ($('view').contains(target) && target.matches('.sheet input')) target.blur();
    else $('edit-form')?.requestSubmit();
    return;
  }
  if (event.key === 'Escape') {
    const open = document.querySelector('details.new-item[open], details.shortcuts[open]');
    if (open) { open.open = false; open.querySelector('summary').focus(); }
    else if (typing(target)) target.blur();
    else $('toasts').lastElementChild?.remove();
    return;
  }
  if (typing(target) || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.key === '/') { event.preventDefault(); $('find').focus(); return; }
  if (!['Timeline', 'Subway'].includes(tab)) return;
  const action = {'+': () => zoom(.5), '=': () => zoom(.5), '-': () => zoom(2), '_': () => zoom(2), '0': () => { fit(); renderView(); }}[event.key];
  if (action) { event.preventDefault(); action(); }
});
window.addEventListener('beforeunload', event => { if (anyDirty()) { event.preventDefault(); event.returnValue = ''; } });
// Charts are drawn at the box's real width; redraw when it changes (window resize, a scrollbar appearing).
new ResizeObserver(() => {
  const box = $('view').querySelector('.scroll.chart'), svg = box?.querySelector('#time-chart');
  if (svg && Math.abs(box.clientWidth - Number(svg.getAttribute('width'))) > 1 && !dragging) scheduleRender();
}).observe($('view'));

document.title = `${worldName} · Lorekeeper`;
$('mode').hidden = !saga;
$('new-item').hidden = saga;
try { await refresh(); idle(); }
catch (error) { report(error, [], 'Could not load'); }
async function poll() {
  if (refreshing || dragging || document.hidden) return;
  try {
    const response = await fetch('/api/stamp');
    if (!response.ok) throw new Error('stamp');
    const {stamp} = await response.json();
    if (offline) { offline = false; idle(); }
    if (stamp !== lastStamp) await refresh();
  } catch {
    if (!offline) { offline = true; idle(); }
  }
}
setInterval(poll, 2000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
