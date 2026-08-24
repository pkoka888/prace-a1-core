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

function renderApprovals() {
  const data = window.APPROVAL_REGISTER;
  const dashboard = select('#approval-dashboard');
  if (!data || !dashboard) return;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  dashboard.innerHTML = (data.records || []).map((record) => {
    const passed = (record.checks || []).filter((item) => ['passed', 'not-required'].includes(item.status)).length;
    const choices = (record.choices || []).map((choice) => '<li><span class="approval-mark">' + (choice.approval === 'approved' ? '✓' : '◌') + '</span><div><b>' + esc(choice.label) + '</b><small>' + esc(choice.selected) + '</small></div><em>' + esc(choice.approval) + '</em></li>').join('');
    const checks = (record.checks || []).map((check) => '<li class="check-' + esc(check.status) + '"><span>' + (check.status === 'passed' ? '✓' : '○') + '</span><div><b>' + esc(check.label) + '</b><small>' + esc(check.evidence || 'Evidence zatím nepřiložena') + '</small></div><em>' + esc(check.status) + '</em></li>').join('');
    return '<article class="approval-card"><header><div><p>' + esc(record.id) + '</p><h2>' + esc(record.title) + '</h2></div><span class="approval-state ' + esc(record.human_decision) + '">' + (record.human_decision === 'approved' ? '✓ Schváleno' : esc(record.human_decision)) + '</span></header>'
      + '<p class="approval-scope">' + esc(record.scope) + '</p><div class="approval-meta"><span><b>Schválil</b>' + esc(record.approver) + '</span><span><b>Datum</b>' + esc(record.approved_at || '—') + '</span><span><b>Validace</b>' + passed + '/' + (record.checks || []).length + '</span></div><label class="review-confirm"><input type="checkbox" data-review-id="' + esc(record.id) + '"> Potvrzuji zobrazené volby a rozsah rozhodnutí</label>'
      + '<div class="approval-grid"><section><h3>Schválené volby</h3><ul>' + choices + '</ul></section><section><h3>Technické kontroly</h3><ul>' + checks + '</ul></section></div>'
      + '<footer><div class="gate-status ' + esc(record.implementation_gate) + '"><b>Implementace: ' + esc(record.implementation_gate) + '</b><span>' + esc(record.implementation_gate_reason || '') + '</span></div><div class="gate-status ' + esc(record.activation_gate) + '"><b>Reálná data: ' + esc(record.activation_gate) + '</b><span>' + esc(record.activation_gate_reason || '') + '</span></div></footer></article>';
  }).join('');
}

const exportApproval = select('#export-approval');
if (exportApproval) exportApproval.addEventListener('click', () => {
  const reviewer = select('#approval-reviewer').value.trim();
  const reviewedAt = select('#approval-review-date').value;
  const confirmed = selectAll('[data-review-id]:checked').map((item) => item.dataset.reviewId);
  if (!reviewer || !reviewedAt || confirmed.length === 0) {
    select('#approval-export-status').textContent = ' Vyplňte schvalovatele, datum a označte alespoň jednu kartu.';
    return;
  }
  const payload = {schema_version: '1.0', receipt_type: 'human-approval-review', exported_at: new Date().toISOString(), reviewer, reviewed_at: reviewedAt, note: select('#approval-review-note').value.trim() || null, confirmed_records: confirmed, records: window.APPROVAL_REGISTER.records.filter((record) => confirmed.includes(record.id))};
  const blob = new Blob([JSON.stringify(payload, null, 2) + '\n'], {type: 'application/json'});
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = 'approval-receipt.json';
  link.click();
  URL.revokeObjectURL(link.href);
  select('#approval-export-status').textContent = ' Doklad exportován; registr se automaticky nemění.';
});

renderApprovals();

const exportJanPhase1 = select('#export-jan-phase1');
if (exportJanPhase1) exportJanPhase1.addEventListener('click', () => {
  const area = select('#jan-exception-area').value;
  const note = select('#jan-exception-note').value.trim();
  const defaultsAccepted = select('#jan-approve-defaults').checked;
  if (area && !note) { select('#jan-phase1-status').textContent = ' Popište výjimku bez osobních údajů.'; return; }
  const payload = {schema_version: '1.0', receipt_type: 'jan-phase-1-exception', defaults_accepted: defaultsAccepted, exception: area ? {area, note} : null, source: 'docs/release-1a/unblock-review-packet.md'};
  const blob = new Blob([JSON.stringify(payload, null, 2) + '\n'], {type: 'application/json'});
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'jan-phase-1-exception.json'; link.click(); URL.revokeObjectURL(link.href);
  select('#jan-phase1-status').textContent = area ? ' Výjimka exportována.' : ' Potvrzení bez výjimky exportováno.';
});
