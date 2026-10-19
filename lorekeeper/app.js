// Lorekeeper's start screen: the person's worlds, a new world, or a folder. Plain words only;
// every change is a POST with this run's token. Page text is set with textContent, never as HTML.
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="lore-token"]').content;
let state = {worlds: [], parent: '', picker: true}, parent = null;

function el(tag, text, attributes = {}) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  for (const [key, value] of Object.entries(attributes)) if (value != null) node.setAttribute(key, value);
  return node;
}
function button(text, action, attributes = {}) {
  const node = el('button', text, {type: 'button', ...attributes});
  node.addEventListener('click', () => action(node));
  return node;
}
function status(text) { $('status').textContent = text; }

async function post(action, args = {}) {
  let response;
  try {
    response = await fetch(`/api/${action}`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Lore-Token': token},
      body: JSON.stringify(args)});
  } catch {
    throw new Error('Lorekeeper isn’t running. Open it again from its icon.');
  }
  const reply = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(reply.error || 'Something went wrong. Try again.');
  return reply;
}

// Waiting on the server: the button says what is happening and cannot be pressed twice.
async function busy(node, text, work) {
  const label = node.textContent;
  node.disabled = true; node.textContent = text;
  try { return await work(); }
  finally { node.disabled = false; node.textContent = label; }
}

function ask(title, text, ok, cancel = 'Cancel') {
  $('ask-title').textContent = title; $('ask-text').textContent = text;
  $('ask-ok').textContent = ok; $('ask-cancel').textContent = cancel;
  const dialog = $('ask');
  dialog.returnValue = '';
  dialog.showModal();
  return new Promise(resolve => dialog.addEventListener('close', () => resolve(dialog.returnValue === 'ok'), {once: true}));
}

function opened(iso) {
  const then = new Date(iso), now = new Date();
  if (Number.isNaN(then.getTime())) return '';
  const days = Math.round((new Date(now.toDateString()) - new Date(then.toDateString())) / 864e5);
  if (days <= 0) return 'Opened today';
  if (days === 1) return 'Opened yesterday';
  if (days < 30) return `Opened ${days} days ago`;
  return `Opened ${then.toLocaleDateString(undefined, {day: 'numeric', month: 'long', year: 'numeric'})}`;
}

const AI_MESSAGE = 'This folder is a Lorekeeper story world. Before you read or change anything, read AGENTS.md in this folder '
  + 'and the guide it points to (.lore/AI-GUIDE.md), then follow them. Explain what you change in plain words.';

function aiNote(world) {
  const box = el('details', null, {class: 'ai-note'});
  box.append(el('summary', 'Using an AI assistant'));
  const body = el('div', null, {class: 'ai-body'});
  body.append(el('p', 'This world includes instructions written for AI assistants such as Claude. '
    + 'Open the world’s folder in your assistant, and it will know how your world fits together and how to change it safely.'));
  const done = el('span', '', {class: 'hint', role: 'status'});
  const row = el('div', null, {class: 'row'});
  row.append(
    button('Copy a message for your assistant', async () => {
      try { await navigator.clipboard.writeText(AI_MESSAGE); done.textContent = 'Copied. Paste it into your assistant.'; }
      catch { done.textContent = 'Copying isn’t allowed here. Ask your assistant to read AGENTS.md in the world’s folder.'; }
    }),
    button('Show the folder', () => post('show', {folder: world.folder}).catch(error => status(error.message)), {class: 'quiet'}),
    done);
  body.append(row);
  box.append(body);
  return box;
}

function worldCard(world) {
  const card = el('li', null, {class: `world-card${world.kind === 'missing' ? ' missing' : ''}`});
  const head = el('div', null, {class: 'world-head'});
  const name = el('h2', world.name);
  head.append(name);
  if (world.kind === 'saga') head.append(el('span', 'Saga · proposals only', {class: 'mode'}));
  if (world.open && world.kind !== 'missing') head.append(el('span', 'Open', {class: 'open-badge'}));
  card.append(head, el('p', world.folder, {class: 'path'}));
  const meta = el('p', world.kind === 'missing' ? 'Folder not found. It may have been moved, renamed or deleted.' : opened(world.opened),
    {class: world.kind === 'missing' ? 'warning' : 'hint'});
  card.append(meta);
  const actions = el('div', null, {class: 'row'});
  if (world.kind !== 'missing') {
    actions.append(button('Open', node => busy(node, world.kind === 'saga' ? 'Opening the saga…' : 'Opening…',
      () => openFolder(world.folder)).catch(error => status(error.message)),
      {class: 'primary', 'aria-label': `Open ${world.name}`}));
  }
  actions.append(button('Remove from list', async () => {
    if (!await ask(`Remove ${world.name} from the list?`, 'Only the list changes. The world’s folder and files stay exactly where they are.',
      'Remove from list')) return;
    await post('forget', {folder: world.folder}).catch(error => status(error.message));
    status(`${world.name} was removed from the list. Its files are untouched.`);
    await load();
    $('open-folder').focus();
  }, {class: 'quiet', 'aria-label': `Remove ${world.name} from the list`}));
  card.append(actions);
  if (world.kind === 'world') card.append(aiNote(world));
  return card;
}

function render() {
  const list = $('world-list');
  list.replaceChildren(...state.worlds.map(worldCard));
  $('worlds-empty').hidden = state.worlds.length > 0;
  showPlace();
  $('change-place').hidden = !state.picker;
  $('place-input').hidden = state.picker;
}

function folderName(name) {
  const text = name.replace(/[<>:"/\\|?*\x00-\x1f]/g, ' ').replace(/\s+/g, ' ').trim().replace(/^[ .]+|[ .]+$/g, '');
  return text || 'My world';
}
function separator() { return (parent || state.parent).includes('\\') ? '\\' : '/'; }
function showPlace() {
  const base = parent || state.parent;
  $('place').textContent = `${base}${separator()}${folderName($('new-name').value)}`;
  if (!state.picker && !$('place-input').value) $('place-input').value = base;
}

async function load() {
  const response = await fetch('/api/worlds');
  state = await response.json();
  render();
}

async function openFolder(folder, make = false) {
  const reply = await post('open', {folder, make});
  if (reply.offer === 'make') {
    const yes = await ask(`“${reply.name}” isn’t a Lorekeeper world yet`,
      'Make it one? Your files stay exactly as they are. Lorekeeper adds a small settings file so it can open the folder as a world.',
      'Make it a world');
    if (yes) return openFolder(folder, true);
    return;
  }
  window.location.assign(reply.url);
}

$('new-name').addEventListener('input', () => { showPlace(); $('new-error').textContent = ''; $('new-name').removeAttribute('aria-invalid'); });
$('change-place').addEventListener('click', () => busy($('change-place'), 'Choosing…', async () => {
  const {folder} = await post('pick', {title: 'Choose where to keep your world', start: parent || state.parent});
  if (folder) { parent = folder; showPlace(); }
}).catch(error => { $('new-error').textContent = error.message; }));
$('new-form').addEventListener('submit', event => {
  event.preventDefault();
  const name = $('new-name').value.trim();
  if (!name) {
    $('new-error').textContent = 'Give your world a name.';
    $('new-name').setAttribute('aria-invalid', 'true');
    $('new-name').focus();
    return;
  }
  const template = new FormData($('new-form')).get('start') || null;
  const chosen = state.picker ? (parent || state.parent) : $('place-input').value.trim();
  busy($('create'), 'Creating…', async () => {
    const reply = await post('create', {name, template, parent: chosen});
    window.location.assign(reply.url);
  }).catch(error => { $('new-error').textContent = error.message; });
});
$('open-folder').addEventListener('click', () => busy($('open-folder'), 'Choosing…', async () => {
  let folder;
  if (state.picker) folder = (await post('pick', {title: 'Choose a folder to open'})).folder;
  else folder = window.prompt('Type the location of the folder to open');
  if (folder) await openFolder(folder.trim());
}).catch(error => status(error.message)));
$('close-app').addEventListener('click', async () => {
  if (!await ask('Close Lorekeeper?', 'Any world you have open in another tab will stop working. Save your changes there first.',
    'Close Lorekeeper', 'Keep working')) return;
  try { await post('quit'); } catch { /* already closed */ }
  $('home').hidden = true;
  document.querySelector('.topbar').querySelectorAll('button').forEach(node => { node.hidden = true; });
  $('closed').hidden = false;
  document.title = 'Lorekeeper is closed';
});
// Coming back to this tab after opening a world: refresh what is open.
document.addEventListener('visibilitychange', () => { if (!document.hidden && $('closed').hidden) load().catch(() => {}); });

load().catch(() => status('Lorekeeper isn’t running. Open it again from its icon.'));
