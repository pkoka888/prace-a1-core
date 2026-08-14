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

// --- Planning catalog (derived from planning/catalog.json) ---
function renderCatalog() {
  const data = window.PLANNING_CATALOG;
  if (!data) return;
  const el = (id) => document.getElementById(id);
  const repoLink = (p) => '../../..' + '/' + p;

  if (el('catalog-generated')) {
    el('catalog-generated').textContent = 'Aktualizováno: ' + (data.generated_or_reviewed_at || '?');
  }

  const laneName = {
    'critical-path': 'Teď (kritická cesta Release 1A)',
    'parallel': 'Paralelně (neblokující)',
    'a1-lane': 'Samostatné A1 operace',
  };
  const laneCat = { 'critical-path': 'now', 'parallel': 'parallel', 'a1-lane': 'gated' };
  let lanesHtml = '<div class="catalog-lanes">';
  (data.lanes || []).forEach((l) => {
    const cls = laneCat[l.id] || 'gated';
    const deps = (l.deps || []).join(', ');
    lanesHtml += '<section class="catalog-lane ' + cls + '"><header><span class="lane-dot ' + cls + '"></span>'
      + '<h2>' + (laneName[l.id] || l.id) + '</h2><b>' + (l.status || '') + '</b></header>'
      + '<p>' + (l.title || '') + '</p><footer>Závislosti: ' + (deps || 'žádné') + '</footer></section>';
  });
  lanesHtml += '</div>';
  lanesHtml += '<section class="catalog-release1a"><header><h2>Release 1A cesta</h2></header><p>'
    + (data.release_1a_path || []).join(' → ') + '</p></section>';
  if (el('catalog-lanes')) el('catalog-lanes').innerHTML = lanesHtml;

  let plansHtml = '<table class="catalog-table"><thead><tr><th>ID</th><th>Název</th><th>Stav</th>'
    + '<th>Milník</th><th>Vlastník</th><th>Rozhodnutí</th><th>Spustitelné</th><th>Zdroje</th></tr></thead><tbody>';
  (data.plans || []).forEach((p) => {
    const sources = (p.sources || []).map((s) => '<a href="' + repoLink(s) + '">' + s + '</a>').join(' ');
    plansHtml += '<tr><td>' + p.id + '</td><td>' + (p.title || '') + '</td><td><span class="cat-status ' + (p.status || '') + '">'
      + (p.status || '') + '</span></td><td>' + (p.milestone || '') + '</td><td>' + (p.owner || '') + '</td><td>'
      + (p.decision_state || '') + '</td><td>' + (p.executable ? 'ano' : 'ne') + '</td><td class="cat-sources">' + (sources || '') + '</td></tr>';
  });
  plansHtml += '</tbody></table>';
  if (el('catalog-plans')) el('catalog-plans').innerHTML = plansHtml;

  let decHtml = '<table class="catalog-table"><thead><tr><th>ID</th><th>Rozhodnutí</th><th>Stav</th>'
    + '<th>Schváleno</th><th>Datum</th></tr></thead><tbody>';
  (data.decisions || []).forEach((d) => {
    decHtml += '<tr><td>' + d.id + '</td><td>' + (d.title || '') + '</td><td><span class="cat-status ' + (d.state || '') + '">'
      + (d.state || '') + '</span></td><td>' + (d.approver || '') + '</td><td>' + (d.date || '—') + '</td></tr>';
  });
  decHtml += '</tbody></table>';
  if (el('catalog-decisions')) el('catalog-decisions').innerHTML = decHtml;

  let flagsHtml = '<section class="catalog-flag-block"><h2>Chybějící brány / evidence</h2><ul>';
  (data.missing_gate_items || []).forEach((id) => {
    flagsHtml += '<li class="cat-warn">⚠ ' + id + ': chybí quality_gate nebo evidence_state</li>';
  });
  flagsHtml += '</ul></section>';
  flagsHtml += '<section class="catalog-flag-block"><h2>Historické / zrušené (ne-spustitelné)</h2><ul>';
  (data.historical_or_superseded || []).forEach((h) => {
    flagsHtml += '<li class="cat-dim">⊘ ' + h.id + ' (' + h.status + ') → nástupce ' + (h.successor || '?') + '</li>';
  });
  flagsHtml += '</ul></section>';
  if (el('catalog-flags')) el('catalog-flags').innerHTML = flagsHtml;
}

selectAll('[data-catalog-view]').forEach((button) => button.addEventListener('click', () => {
  const view = button.dataset.catalogView;
  selectAll('[data-catalog-view]').forEach((b) => b.classList.toggle('active', b === button));
  ['lanes', 'plans', 'decisions', 'flags'].forEach((v) => {
    const panel = select('#catalog-' + v);
    if (panel) panel.classList.toggle('active', v === view);
  });
}));

renderCatalog();
