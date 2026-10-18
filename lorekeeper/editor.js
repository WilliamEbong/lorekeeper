// No dependency or build step. Drafts retain the exact graph snapshot they came from.
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="lore-token"]').content;
const saga = document.querySelector('meta[name="lore-saga"]').content === 'true';
const calendars = JSON.parse(document.querySelector('meta[name="lore-calendars"]').content);
const drafts = new Map(), cells = new Map(), conversions = new Map();
let graph = {items: [], links: [], types: {}, roles: {}}, selected = '', tab = 'Timeline';
let range = null, lastStamp = null, refreshing = false, dragging = false, subwayFilter = '';
let refreshQueue = Promise.resolve();
const ref = (item) => item.id || item.name;
const person = (item) => graph.types[item.type]?.category === 'person';
const startKey = (item) => ['born', 'date', 'start'].find(k => item.fields[k]) || (person(item) ? 'born' : 'date');
const endKey = (item) => ['died', 'end'].find(k => item.fields[k]) || (person(item) ? 'died' : 'end');
const nameKey = (item) => item.fields.canonical_name != null ? 'canonical_name' : 'name';
const display = (value) => Array.isArray(value) ? JSON.stringify(value) : String(value ?? '');
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const dated = () => graph.items.filter(i => i.lo != null).sort((a, b) => a.lo - b.lo || a.name.localeCompare(b.name));
const people = () => graph.items.filter(person).sort((a, b) => a.name.localeCompare(b.name));
const events = () => dated().filter(i => !person(i));
const takesPart = (p, e) => graph.links.some(l => l.role === 'participants' && l.from === ref(e) && l.to === ref(p) && l.resolved);

function el(tag, text, attributes = {}) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}
function svgEl(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text != null) node.textContent = text;
  return node;
}
function button(text, action, attributes = {}) {
  const node = el('button', text, {type: 'button', ...attributes});
  node.addEventListener('click', () => Promise.resolve().then(action).catch(report));
  return node;
}
function status(text) { $('status').textContent = text; }
function report(error) {
  status('Not saved. See the message below; your input is kept.');
  $('error').hidden = false;
  $('error').textContent = error.message || String(error);
}
async function api(name, args = {}) {
  const response = await fetch(`/api/${name}`, {method: 'POST', headers: {
    'Content-Type': 'application/json', 'X-Lore-Token': token}, body: JSON.stringify(args)});
  const result = await response.json();
  if (!response.ok) {
    const err = result.error || {message: response.statusText};
    throw new Error(`${err.code || response.status}: ${err.message}${err.data ? '\nCurrent values: ' + JSON.stringify(err.data.current ?? err.data, null, 2) : ''}`);
  }
  return result;
}
function valueOf(text, original) {
  // Existing list fields stay lists. Other fields remain literal text, including numeric dates.
  if (!Array.isArray(original)) return text;
  const value = JSON.parse(text || '[]');
  if (!Array.isArray(value) || value.some(v => typeof v !== 'string')) throw new Error('List fields need a JSON array of strings.');
  return value;
}
function draftFor(item) {
  if (!drafts.has(item.path)) drafts.set(item.path, {base: item, values: Object.create(null), note: ''});
  return drafts.get(item.path);
}
function dirty(draft) { return draft && (Object.keys(draft.values).length > 0 || draft.note); }
function fieldsFor(item) {
  return [...new Set([nameKey(item), 'type', startKey(item), endKey(item), 'location', ...Object.keys(item.fields)])];
}
function addInput(parent, key, value, onInput, attributes = {}) {
  const id = `field-${key}`;
  parent.append(el('label', key, {for: id}));
  const input = el('input', null, {id, name: key, ...attributes});
  input.value = value;
  input.addEventListener('input', () => onInput(input.value));
  parent.append(input);
  return input;
}
function selectItem(path, focus = false) {
  selected = path;
  $('item-select').value = path;
  renderInspector();
  document.querySelectorAll('svg .item').forEach(node => node.classList.toggle('selected', node.dataset.path === path));
  if (focus) $('inspector').querySelector('input')?.focus();
}
function renderInspector() {
  const panel = $('inspector'), item = graph.items.find(i => i.path === selected);
  panel.replaceChildren();
  if (!item) { panel.append(el('p', 'Select an item to see its fields and connections.')); return; }
  let draft = draftFor(item);
  if (!dirty(draft)) { draft = {base: item, values: Object.create(null), note: ''}; drafts.set(item.path, draft); }
  const form = el('form', null, {id: 'edit-form'});
  for (const key of fieldsFor(draft.base)) {
    addInput(form, key, draft.values[key] ?? display(draft.base.fields[key]), value => {
      if (value === display(draft.base.fields[key])) delete draft.values[key];
      else draft.values[key] = value;
    }, key === 'id' ? {readonly: ''} : {});
  }
  form.append(el('p', 'List fields use ["value", "value"]. Dates can always be edited here.', {class: 'hint'}));
  if (saga) {
    form.append(el('label', 'Change note', {for: 'change-note'}));
    const note = el('textarea', null, {id: 'change-note', required: ''});
    note.value = draft.note;
    note.addEventListener('input', () => { draft.note = note.value; });
    form.append(note);
  }
  form.append(el('button', saga ? 'Propose change' : 'Save', {type: 'submit', class: 'primary'}));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    // Link controls also wait for a save's reload, so their selected target cannot
    // be reset between choosing it and pressing Add link.
    const controls = [...panel.querySelectorAll('input, select, textarea, button')];
    try {
      const field = Object.fromEntries(Object.entries(draft.values).map(([k, v]) => [k, valueOf(v, draft.base.fields[k])]));
      controls.forEach(c => { c.disabled = true; });
      if (saga) {
        await api('request', {item: ref(draft.base), field, note: draft.note});
        status('Change request queued. Canon is unchanged.');
      } else {
        await saveFields(draft.base, field);
      }
      drafts.delete(item.path);
      $('error').hidden = true;
      await refresh();
      renderInspector();
    } catch (error) { report(error); }
    finally { controls.forEach(c => { c.disabled = false; }); }
  });
  panel.append(form);
  renderLinks(panel, item);
}
async function saveFields(base, field) {
  if (!Object.keys(field).length) return;
  const expect = Object.fromEntries(Object.keys(field).map(k => [k, base.fields[k] ?? null]));
  const result = await api('set', {item: ref(base), field, version: base.version, expect});
  status(result.merged ? 'Saved; merged with changes to other fields.' : 'Saved.');
  return result;
}
function renderLinks(panel, item) {
  panel.append(el('h3', 'Links'));
  const list = el('ul');
  for (const link of graph.links.filter(l => l.from === ref(item))) {
    const target = graph.items.find(i => ref(i) === link.to);
    const row = el('li', `${link.role} → ${target?.name || link.to}${link.resolved ? '' : ' (unresolved)'}`);
    if (!saga) row.append(button('Remove link', async () => {
      await api('unlink', {item: ref(item), role: link.role, target: target?.name || link.to});
      await refresh(); renderInspector(); status('Link removed.');
    }, {'aria-label': 'Remove link', title: `${link.role} → ${target?.name || link.to}`}));
    list.append(row);
  }
  panel.append(list.childElementCount ? list : el('p', 'No outgoing links.'));
  panel.append(el('h3', 'Backlinks'));
  const backlinks = el('ul');
  for (const link of graph.links.filter(l => l.to === ref(item) && l.resolved)) {
    const source = graph.items.find(i => ref(i) === link.from);
    const row = el('li', `${graph.roles[link.role]?.inverse || link.role}: `);
    if (source) row.append(button(source.name, () => selectItem(source.path)));
    backlinks.append(row);
  }
  panel.append(backlinks.childElementCount ? backlinks : el('p', 'No backlinks.'));
  if (saga) { panel.append(el('p', 'Propose links using the field inputs or describe them in the change note.', {class: 'hint'})); return; }
  panel.append(el('label', 'Link role', {for: 'link-role'}));
  const roles = el('select', null, {id: 'link-role'});
  for (const [key, role] of Object.entries(graph.roles)) roles.append(el('option', role.label || key, {value: key}));
  panel.append(roles, el('label', 'Link target', {for: 'link-target'}));
  const targets = el('select', null, {id: 'link-target'});
  for (const target of graph.items) targets.append(el('option', target.name, {value: ref(target)}));
  panel.append(targets, button('Add link', async () => {
    await api('link', {item: ref(item), role: roles.value, target: targets.value});
    await refresh(); renderInspector(); status('Link added.');
  }));
}

// The axis uses Lorekeeper's integer minutes since 0001-01-01, not Unix milliseconds.
// This Gregorian inverse mirrors dates.civil_from_days and works beyond JS Date's range.
function gregorian(minute, precision = 'day') {
  const n = Math.floor(minute / 1440) + 306;
  const era = Math.floor(n / 146097), doe = n - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  let year = yoe + era * 400;
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153), day = doy - Math.floor((153 * mp + 2) / 5) + 1;
  const month = mp + (mp < 10 ? 3 : -9);
  year += month <= 2 ? 1 : 0;
  const pad = n => String(n).padStart(2, '0');
  let out = (year < 0 ? '-' : '') + String(Math.abs(year)).padStart(4, '0');
  if (precision === 'year') return out;
  out += '-' + pad(month);
  if (precision === 'month') return out;
  out += '-' + pad(day);
  if (precision === 'day') return out;
  const time = ((Math.floor(minute) % 1440) + 1440) % 1440;
  return out + ' ' + pad(Math.floor(time / 60)) + ':' + pad(time % 60);
}
function fit() {
  const items = dated();
  const lo = items.length ? Math.min(...items.map(i => i.lo)) : 0;
  const hi = items.length ? Math.max(...items.map(i => i.hi)) : 525600;
  const pad = Math.max(1440, (hi - lo) * .06);
  range = [lo - pad, hi + pad];
}
function zoom(factor, anchor = .5) {
  const span = Math.max(60, (range[1] - range[0]) * factor), center = range[0] + (range[1] - range[0]) * anchor;
  range = [center - span * anchor, center + span * (1 - anchor)]; renderView();
}
function pan(direction) {
  const shift = (range[1] - range[0]) * direction;
  range = range.map(v => v + shift); renderView();
}
function chart(height, title) {
  if (!range) fit();
  const box = el('div', null, {class: 'scroll'});
  const svg = svgEl('svg', {viewBox: `0 0 1000 ${height}`, role: 'group', 'aria-label': title, id: 'time-chart'});
  const x = minute => 170 + (minute - range[0]) / (range[1] - range[0]) * 800;
  const inverse = pos => range[0] + (pos - 170) / 800 * (range[1] - range[0]);
  const px = event => (event.clientX - svg.getBoundingClientRect().left) / svg.getBoundingClientRect().width * 1000;
  svg.append(svgEl('text', {x: 12, y: 20}, 'Gregorian axis'));
  for (let tick = 0; tick <= 5; tick++) {
    const pos = 170 + tick * 160;
    svg.append(svgEl('line', {x1: pos, x2: pos, y1: 32, y2: height - 10, class: 'axis'}));
    svg.append(svgEl('text', {x: pos, y: 20, 'text-anchor': tick === 5 ? 'end' : 'start'}, gregorian(inverse(pos), 'day')));
  }
  svg.addEventListener('wheel', event => {
    if (!event.ctrlKey) return;
    event.preventDefault(); zoom(event.deltaY > 0 ? 1.25 : .8, Math.max(0, Math.min(1, (px(event) - 170) / 800)));
  }, {passive: false});
  svg.addEventListener('pointerdown', event => {
    if (event.target.closest('.item') || event.button !== 0) return;
    const start = px(event), initial = [...range];
    dragging = true; svg.setPointerCapture(event.pointerId);
    const finish = e => {
      const shift = (px(e) - start) / 800 * (initial[1] - initial[0]);
      range = initial.map(v => v - shift); dragging = false;
      svg.removeEventListener('pointerup', finish); svg.removeEventListener('pointercancel', cancel);
      renderView();
    };
    const cancel = () => { dragging = false; svg.removeEventListener('pointerup', finish); svg.removeEventListener('pointercancel', cancel); };
    svg.addEventListener('pointerup', finish); svg.addEventListener('pointercancel', cancel);
  });
  box.append(svg);
  return {box, svg, x, inverse, px};
}
function timeToolbar(container) {
  const toolbar = el('div', null, {class: 'toolbar'});
  toolbar.append(button('Zoom in', () => zoom(.5)), button('Zoom out', () => zoom(2)),
    button('Pan left', () => pan(-.25)), button('Pan right', () => pan(.25)), button('Fit all', () => { fit(); renderView(); }));
  container.append(toolbar);
}
function timeline(container) {
  timeToolbar(container);
  container.append(el('p', saga ? 'Select an item to propose a change.' : 'Drag a Gregorian item to re-date it. Arrow keys select; Enter opens its fields. Ctrl+wheel zooms; drag the background to pan.', {class: 'hint'}));
  const items = dated().sort((a, b) => a.type.localeCompare(b.type) || a.lo - b.lo);
  const c = chart(Math.max(180, items.length * 42 + 64), 'Timeline');
  items.forEach((item, index) => {
    const y = 64 + index * 42;
    c.svg.append(svgEl('text', {x: 12, y: y + 5}, index === 0 || item.type !== items[index - 1].type ? item.type : ''));
    c.svg.append(svgEl('line', {x1: 160, x2: 980, y1: y + 18, y2: y + 18, class: 'lane'}));
    const x = c.x(item.lo), width = c.x(item.hi) - x;
    if (x > 970 || x + width < 170) return;
    const group = svgEl('g', {class: `item${selected === item.path ? ' selected' : ''}`, role: 'button', tabindex: '0',
      'aria-label': `${item.name}, ${item.start.text}`, 'data-path': item.path, 'data-item': ref(item), id: `timeline-${encodeURIComponent(ref(item))}`});
    group.append(svgEl('title', {}, `${item.name}: ${item.start.text}`));
    if (width < 1) group.append(svgEl('circle', {cx: x, cy: y, r: 6, class: 'mark'}));
    else group.append(svgEl('rect', {x: Math.max(170, x), y: y - 8, width: Math.max(2, Math.min(970, x + width) - Math.max(170, x)), height: 16, rx: 3, class: 'mark'}));
    group.append(svgEl('text', {x: Math.max(175, Math.min(x, 785)), y: y - 14}, item.name));
    group.addEventListener('click', () => selectItem(item.path));
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectItem(item.path, true); }
      if (['ArrowLeft', 'ArrowUp', 'ArrowRight', 'ArrowDown'].includes(event.key)) {
        event.preventDefault();
        const nodes = [...c.svg.querySelectorAll('.item')], current = nodes.indexOf(group);
        const next = nodes[Math.max(0, Math.min(nodes.length - 1, current + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -1 : 1)))];
        next.focus(); selectItem(next.dataset.path);
      }
    });
    if (!saga) enableRedate(group, item, c);
    c.svg.append(group);
  });
  container.append(c.box);
  if (!items.length) container.append(el('p', 'No dated items yet. Create one, then enter its date in the inspector.'));
}
function enableRedate(group, item, c) {
  group.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    event.stopPropagation();
    selectItem(item.path);
    const start = c.px(event), origin = c.x(item.lo), initialRange = [...range];
    // Identify the parser before allowing visual movement, rather than guessing
    // from the date's spelling (a custom calendar can also display ISO dates).
    let allowed = false;
    const conversion = (async () => {
      if (!conversions.has(item.start.text)) conversions.set(item.start.text, await api('convert', {date: item.start.text}));
      const converted = conversions.get(item.start.text);
      const cal = calendars.find(c => (c.id || c.type || 'gregorian') === converted.parsed_by);
      allowed = Boolean(cal && (cal.type || 'gregorian') === 'gregorian' && ['year', 'month', 'day', 'minute'].includes(item.start.precision));
      return allowed;
    })();
    // Attach a rejection handler immediately, even when a pointer is cancelled.
    conversion.catch(report);
    dragging = true; group.setPointerCapture(event.pointerId);
    const move = e => { if (allowed) { group.classList.add('dragging'); group.setAttribute('transform', `translate(${c.px(e) - start},0)`); } };
    const cleanup = () => {
      dragging = false; group.removeAttribute('transform'); group.classList.remove('dragging');
      group.removeEventListener('pointermove', move); group.removeEventListener('pointerup', finish); group.removeEventListener('pointercancel', cleanup);
    };
    const finish = async e => {
      const dx = c.px(e) - start; cleanup();
      if (Math.abs(dx) < 3) return;
      try {
        if (!await conversion) {
          status('Drag is unavailable for this calendar or precision. Edit the date input instead.'); return;
        }
        const minute = initialRange[0] + (origin + dx - 170) / 800 * (initialRange[1] - initialRange[0]);
        const key = startKey(item), value = gregorian(Math.round(minute), item.start.precision);
        const draft = draftFor(item);
        if (dirty(draft)) { status('Save your inspector draft before dragging.'); return; }
        draft.values[key] = value;
        // Only the start is changed; explicit end dates remain an intentional separate edit.
        renderInspector();
        await saveFields(item, {[key]: value});
        drafts.delete(item.path); $('error').hidden = true; await refresh();
      } catch (error) { report(error); }
    };
    group.addEventListener('pointermove', move); group.addEventListener('pointerup', finish); group.addEventListener('pointercancel', cleanup);
  });
}
function subway(container) {
  timeToolbar(container);
  const label = el('label', 'Filter people ', {for: 'subway-filter'}), filter = el('input', null, {id: 'subway-filter', type: 'search'});
  filter.value = subwayFilter;
  filter.addEventListener('input', () => {
    const pos = filter.selectionStart; subwayFilter = filter.value; renderView();
    $('subway-filter').focus(); $('subway-filter').setSelectionRange(pos, pos);
  });
  label.append(filter); container.append(label, el('p', 'The 12 people with the most events. Filter to show all matching people.', {class: 'hint'}));
  const allEvents = events();
  const ranked = people().map(p => ({p, count: allEvents.filter(e => takesPart(p, e)).length})).sort((a, b) => b.count - a.count || a.p.name.localeCompare(b.p.name));
  const lanes = (subwayFilter ? ranked.filter(({p}) => p.name.toLowerCase().includes(subwayFilter.toLowerCase())) : ranked.slice(0, 12)).map(r => r.p);
  const c = chart(Math.max(170, lanes.length * 56 + 65), 'Subway');
  lanes.forEach((p, i) => {
    c.svg.append(svgEl('text', {x: 12, y: 65 + i * 56}, p.name));
    c.svg.append(svgEl('line', {x1: 170, x2: 970, y1: 60 + i * 56, y2: 60 + i * 56, class: 'rail'}));
  });
  for (const event of allEvents) {
    const stops = lanes.map((p, i) => takesPart(p, event) ? i : -1).filter(i => i >= 0), x = c.x(event.lo);
    if (!stops.length || x < 170 || x > 970) continue;
    c.svg.append(svgEl('line', {x1: x, x2: x, y1: 60 + stops[0] * 56, y2: 60 + stops.at(-1) * 56, class: 'connector'}));
    for (const lane of stops) {
      const stop = svgEl('g', {class: 'item', role: 'button', tabindex: '0', 'aria-label': `${event.name}, ${lanes[lane].name}`});
      stop.append(svgEl('circle', {cx: x, cy: 60 + lane * 56, r: 7, class: 'mark'}), svgEl('title', {}, `${event.name} · ${event.start.text}`));
      stop.addEventListener('click', () => selectItem(event.path));
      stop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectItem(event.path, true); } });
      c.svg.append(stop);
    }
  }
  container.append(c.box);
}
function tableShell(container, caption, columns) {
  const scroll = el('div', null, {class: 'scroll'}), table = el('table'), head = el('thead'), row = el('tr'), body = el('tbody');
  table.append(el('caption', caption));
  for (const col of columns) row.append(el('th', col, {scope: 'col'}));
  head.append(row); table.append(head, body); scroll.append(table); container.append(scroll);
  return body;
}
function relationships(container) {
  const es = events(), body = tableShell(container, 'Ages at participating events · chronological order', ['Person', ...es.map(e => `${e.name} · ${e.start.text}`)]);
  const jobs = [];
  for (const p of people()) {
    const row = el('tr'), heading = el('th', null, {scope: 'row'});
    heading.append(button(p.name, () => selectItem(p.path))); row.append(heading);
    for (const e of es) {
      const cell = el('td', '·', {class: 'age', 'data-person': ref(p), 'data-event': ref(e)});
      if (takesPart(p, e)) {
        cell.textContent = 'Loading…';
        jobs.push(async () => {
          try { const age = await api('age', {item: ref(p), at: ref(e)}); cell.textContent = age.text; }
          catch (error) { cell.textContent = 'Age unavailable'; cell.title = error.message; }
        });
      }
      row.append(cell);
    }
    body.append(row);
  }
  // A small worker pool avoids flooding a large world's local server with age requests.
  for (let n = 0; n < Math.min(4, jobs.length); n++) (async () => {
    while (jobs.length && body.isConnected) await jobs.shift()();
  })();
}
function spreadsheet(container) {
  const body = tableShell(container, saga ? 'Select an item to propose changes in the inspector.' : 'Edit a cell; Enter or leaving the cell saves it.', ['Name', 'Type', 'Date / born', 'End / died', 'Location', 'Inspector']);
  for (const item of graph.items) {
    const row = el('tr');
    for (const key of [nameKey(item), 'type', startKey(item), endKey(item), 'location']) {
      const cell = el('td'), id = `${item.path}\0${key}`;
      let base = item;
      const input = el('input', null, {'aria-label': `${item.name}: ${key}`, 'data-field': key, 'data-item': ref(item)});
      input.value = cells.get(id)?.value ?? display(item.fields[key]);
      input.readOnly = saga;
      input.addEventListener('input', () => {
        if (!cells.has(id)) cells.set(id, {base, value: input.value, saving: false});
        else cells.get(id).value = input.value;
      });
      const save = async () => {
        const draft = cells.get(id);
        if (!draft || draft.saving) return;
        draft.saving = true; input.readOnly = true;
        try {
          const value = valueOf(draft.value, draft.base.fields[key]);
          const result = await saveFields(draft.base, {[key]: value});
          // Enter keeps focus in this cell; a second edit must expect the first saved value.
          base = {...draft.base, version: result.version, fields: {...draft.base.fields, [key]: value}};
          cells.delete(id); input.classList.remove('failed'); $('error').hidden = true;
          await refresh();
        } catch (error) { input.classList.add('failed'); report(error); }
        finally { draft.saving = false; input.readOnly = saga; }
      };
      input.addEventListener('blur', save);
      input.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); save(); } });
      cell.append(input); row.append(cell);
    }
    const cell = el('td'); cell.append(button('Inspect', () => selectItem(item.path, true), {'aria-label': `Inspect ${item.name}`})); row.append(cell); body.append(row);
  }
}
function narrative(container) {
  // Cards from hosts use chapter/order/number; natural name order is the fallback.
  const order = i => Number(i.fields.chapter ?? i.fields.order ?? i.fields.number ?? i.name.match(/\d+/)?.[0] ?? Infinity);
  const chapters = graph.items.filter(i => ['chapter', 'card'].includes(i.type)).sort((a, b) => order(a) - order(b) || a.name.localeCompare(b.name, undefined, {numeric: true}));
  const list = el('ol', null, {class: 'narrative'});
  let latest = null;
  chapters.forEach((item, index) => {
    const row = el('li'); row.append(button(`${index + 1}. ${item.name}`, () => selectItem(item.path)));
    const backwards = latest != null && item.lo != null && item.lo < latest;
    row.append(el('span', `${item.start?.text || 'Undated'} · ${item.lo == null ? 'Chronology unknown' : backwards ? '↶ Story vs chronology: moves backwards' : '→ Story and chronology aligned'}`));
    if (item.lo != null) latest = Math.max(latest ?? item.lo, item.lo);
    list.append(row);
  });
  container.append(list.childElementCount ? list : el('p', 'No chapters or cards yet. Create a chapter to begin your narrative.'));
}
function renderView() {
  const view = $('view'); view.replaceChildren();
  ({Timeline: timeline, Subway: subway, Relationships: relationships, Spreadsheet: spreadsheet, Narrative: narrative})[tab](view);
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
    if (!stampResponse.ok) throw new Error('Could not read the project stamp.');
    const stamp = (await stampResponse.json()).stamp;
    const next = await api('graph'); graph = next; lastStamp = stamp;
    const selector = $('item-select');
    selector.replaceChildren(el('option', 'Select an item', {value: ''}));
    for (const item of graph.items) selector.append(el('option', `${item.name} (${item.type})`, {value: item.path}));
    selector.value = selected;
    const types = $('create-type'), previous = types.value;
    types.replaceChildren(...Object.keys(graph.types).map(type => el('option', type, {value: type})));
    types.value = previous || (graph.types.event ? 'event' : Object.keys(graph.types)[0]);
    // Keep focused spreadsheet controls and all failed cells alive through polling.
    if (!(tab === 'Spreadsheet' && $('view').contains(document.activeElement)) && !dragging) renderView();
    if (!$('inspector').contains(document.activeElement)) renderInspector();
  } finally { refreshing = false; }
}

const tabs = [...document.querySelectorAll('[role="tab"]')];
function activateTab(node) {
  tab = node.textContent;
  tabs.forEach(t => { t.setAttribute('aria-selected', String(t === node)); t.tabIndex = t === node ? 0 : -1; });
  $('view').setAttribute('aria-labelledby', node.id); renderView();
}
tabs.forEach((node, index) => {
  node.addEventListener('click', () => activateTab(node));
  node.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next != null) { event.preventDefault(); tabs[next].focus(); activateTab(tabs[next]); }
  });
});
$('item-select').addEventListener('change', event => selectItem(event.target.value));
$('mode').textContent = saga ? 'Saga · changes by request' : 'Local world editor';
$('create-form').hidden = saga;
$('create-form').addEventListener('submit', async event => {
  event.preventDefault();
  const submit = event.target.querySelector('button'); submit.disabled = true;
  try {
    const item = await api('create', {type: $('create-type').value, name: $('create-name').value});
    $('create-name').value = ''; selected = item.path;
    await refresh(); selectItem(item.path, true); $('error').hidden = true; status('Created. Add dates and links in the inspector.');
  } catch (error) { report(error); }
  finally { submit.disabled = false; }
});
try { await refresh(); status(`${graph.items.length} items · changes on disk appear automatically.`); }
catch (error) { report(error); }
setInterval(async () => {
  if (refreshing || dragging) return;
  try {
    const response = await fetch('/api/stamp');
    if (!response.ok) throw new Error('Live reload could not read the project stamp.');
    if ((await response.json()).stamp !== lastStamp) await refresh();
  } catch (error) { report(error); }
}, 2000);
