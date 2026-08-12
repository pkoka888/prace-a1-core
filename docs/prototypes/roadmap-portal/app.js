const select = (selector) => document.querySelector(selector);
const selectAll = (selector) => [...document.querySelectorAll(selector)];

function activate(buttons, panels, key, value, prefix) {
  buttons.forEach((button) => {
    const active = button.dataset[key] === value;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  panels.forEach((panel) => panel.classList.toggle('active', panel.id === `${prefix}${value}`));
}

selectAll('.mode-tab').forEach((button) => button.addEventListener('click', () => {
  activate(selectAll('.mode-tab'), selectAll('.mode'), 'mode', button.dataset.mode, 'mode-');
}));

selectAll('.view-button').forEach((button) => button.addEventListener('click', () => {
  activate(selectAll('.view-button'), selectAll('.roadmap-view'), 'view', button.dataset.view, 'view-');
}));

function showScreen(name) {
  activate(selectAll('.screen-link'), selectAll('.screen'), 'screen', name, 'screen-');
}

selectAll('.screen-link').forEach((button) => button.addEventListener('click', () => showScreen(button.dataset.screen)));
selectAll('[data-goto]').forEach((button) => button.addEventListener('click', () => showScreen(button.dataset.goto)));

const confirmButton = select('.confirm-button');
if (confirmButton) confirmButton.addEventListener('click', () => {
  const note = select('.confirm-note');
  note.textContent = '✓ Údaje potvrzeny demo administrátorem · právě teď';
  note.style.background = '#dff1e8';
  note.style.color = '#206345';
  confirmButton.textContent = 'Potvrzeno';
  confirmButton.disabled = true;
});
