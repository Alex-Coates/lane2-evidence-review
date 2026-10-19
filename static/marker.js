'use strict';
/* Marker page (version 2.1).
   The browser only displays what the server returns and sends the marker's actions
   (decisions, notes, completion) back to the server API.
   Flags come from two places: the OpenAI critique check (how the student responded to each AI answer) and the wording comparison (final text against the AI turns). Screens follow the team's UI design: queue, review (flags / transcript / final
   submission / notes), completion, analysis method and walkthrough guide. */

let summaries = [], current = null, llmInfo = {mode: 'auto', model: '', key_present: false};
let view = 'queue', tab = 'signals', flagId = null, query = '', filter = 'all', focusTurn = null;

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const guard = fn => async (...args) => { try { await fn(...args); } catch (err) { toast(err.message); } };
const pad = n => String(n).padStart(2, '0');
const slug = type => type.toLowerCase().replace(' ', '-');

function toast(text) {
  $('toast').textContent = text;
  $('toast').style.display = 'block';
  setTimeout(() => { $('toast').style.display = 'none'; }, 3500);
}

/* ---------- talking to the server ---------- */
async function api(path, options = {}) {
  const res = await fetch(path, {credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, ...options});
  let data = null;
  try { data = await res.json(); } catch (e) { /* no JSON body */ }
  if (res.status === 401) { location.href = '/marker/login'; throw new Error('Please sign in again.'); }
  if (!res.ok) throw new Error((data && data.error) || 'Request failed (' + res.status + ').');
  return data;
}

async function loadQueue() {
  const d = await api('/api/submissions');
  llmInfo = d.llm || llmInfo;
  summaries = d.submissions.map(s => ({...s, id: s.ref}));
}

async function openRecord(id) {
  current = await api('/api/submissions/' + encodeURIComponent(id));
  tab = 'signals'; flagId = null; focusTurn = null;
  show('detail');
}

async function goQueue() { await loadQueue(); show('queue'); }

/* ---------- navigation and rendering ---------- */
function show(v) { view = v; render(); window.scrollTo(0, 0); }

function stripText() {
  if (view === 'method') return 'Analysis Method';
  if (view === 'guide') return 'Walkthrough Guide';
  if ((view === 'detail' || view === 'complete') && current) return 'Student Submission Data - ' + current.student;
  return 'Student Submission Data';
}

function render() {
  if ((view === 'detail' || view === 'complete') && !current) view = 'queue';
  document.querySelectorAll('[data-view]').forEach(n => n.classList.toggle('active', n.dataset.view === (view === 'detail' || view === 'complete' ? 'queue' : view)));
  $('strip').textContent = stripText();
  $('main').innerHTML = {queue, detail, complete: completePage, method, guide}[view]();
  bind();
}

/* ---------- review queue ---------- */
function visible() {
  return summaries.filter(r => `${r.student} ${r.topic}`.toLowerCase().includes(query.toLowerCase())
    && (filter === 'all' || (filter === 'flagged' && r.flag_count > 0) || (filter === 'missing' && !r.turn_count) || r.status === filter));
}

function rows() {
  return visible().map(r => `<tr>
      <td><button class="rowlink" data-open="${esc(r.id)}">${esc(r.student)}</button><small>${esc(r.topic)}</small></td>
      <td>${r.turn_count ? r.turn_count : 'Missing transcript'}</td>
      <td>${r.turn_count ? `<span class="flagcount">${r.flag_count}</span>` : '<span class="flagcount">—</span>'}</td>
      <td class="${r.status === 'Reviewed' ? 'status-reviewed' : ''}">${esc(r.status)}</td>
      <td><button class="rowlink" data-open="${esc(r.id)}">Review →</button></td></tr>`).join('')
    || '<tr><td colspan="5" class="empty">No submissions match. Try another search or filter.</td></tr>';
}

function queue() {
  const total = summaries.reduce((n, r) => n + r.flag_count, 0);
  const done = summaries.filter(r => r.status === 'Reviewed').length;
  const missing = summaries.filter(r => !r.turn_count).length;
  const filters = [['all', 'All submissions'], ['flagged', 'With review flags'], ['Not started', 'Not started'], ['In progress', 'In progress'], ['Reviewed', 'Reviewed'], ['missing', 'Missing transcript']];
  return `<div class="eyebrow">MARKER WORKSPACE</div><h1>Review queue</h1>
    <div class="actions"><button class="secondary" id="export-queue">Export queue</button></div>
    <div class="stats">
      <div class="stat"><label>Submissions</label><strong>${pad(summaries.length)}</strong></div>
      <div class="stat"><label>Review flags</label><strong>${pad(total)}</strong></div>
      <div class="stat"><label>Reviewed</label><strong>${pad(done)} / ${summaries.length}</strong></div>
      <div class="stat"><label>Missing transcript</label><strong>${pad(missing)}</strong></div>
    </div>
    <section class="panel flush"><div class="toolbar">
      <label class="sr-only" for="search">Search submissions</label><input id="search" placeholder="Search by ID or topic…" value="${esc(query)}">
      <label class="sr-only" for="filter">Filter submissions</label>
      <select id="filter">${filters.map(([v, t]) => `<option value="${v}" ${filter === v ? 'selected' : ''}>${t}</option>`).join('')}</select></div>
      <div class="table-wrap"><table><thead><tr><th>Submission</th><th>Interactions</th><th>Flags</th><th>Status</th><th></th></tr></thead><tbody id="rows">${rows()}</tbody></table></div></section>`;
}

/* ---------- one submission ---------- */
function eyebrow(r, a) {
  if (!r.turns.length) return 'MISSING EVIDENCE';
  if (tab === 'signals' && !a.flags.length) return 'NO FLAGS';
  return 'SUBMISSION REVIEW';
}

function detail() {
  const r = current, a = r.analysis;
  const tabs = [['signals', 'Review flags'], ['transcript', 'Full transcript'], ['submission', 'Final submission'], ['notes', 'Marker notes']];
  const body = tab === 'signals' ? signals(r, a) : tab === 'transcript' ? transcript(r, a) : tab === 'submission' ? finalText(r, a) : notes(r, a);
  return `<div class="eyebrow">${eyebrow(r, a)}</div><h1>${esc(r.student)}</h1>
    <p class="sub">${esc(r.topic)}${r.turns.length ? '' : ' · No transcript supplied'}</p>
    <div class="actions"><button class="secondary" id="back">← Back to queue</button><button class="secondary" id="export-review">Export review</button><button class="primary" id="complete">Complete review</button></div>
    <div class="tabs" role="tablist">${tabs.map(([v, t]) => `<button class="tab ${tab === v ? 'active' : ''}" role="tab" aria-selected="${tab === v}" data-tab="${v}">${t}</button>`).join('')}</div>
    ${body}`;
}

function substantiveReplies(r) {
  const c = r.critique_check;
  return c.status === 'ok' ? c.assessments.filter(a => a.verdict === 'substantive') : [];
}

function substantiveBoxes(r) {
  return substantiveReplies(r).map(a => `<div class="context-box"><h4>STUDENT · TURN ${a.turn}</h4>${esc(r.turns[a.index].text)}<p class="definition" style="margin:8px 0 0">${esc(a.reason)}</p></div>`).join('');
}

const VERDICT_LABELS = {blind_acceptance: 'Blind acceptance', generic: 'Generic reply', substantive: 'Substantive reply'};
const originLabel = r => (r.critique_check.mode === 'mock' ? 'Simulated check' : 'LLM-assisted');

function checkLine(r) {
  const c = r.critique_check;
  let text;
  if (c.status === 'ok') {
    const how = c.mode === 'mock' ? 'simulated stand-in' : c.mode === 'cached' ? 'saved result' : 'live';
    text = `Critique check: ${how}${c.model ? ' · ' + c.model : ''} · ${c.assessments.length} repl${c.assessments.length === 1 ? 'y' : 'ies'} rated`
      + (c.rejected ? ` · ${c.rejected} rejected (quote not found in the student's text)` : '');
  } else if (c.status === 'not_applicable') text = 'Critique check: no student replies to rate.';
  else if (c.status === 'off') text = 'Critique check: switched off.';
  else text = 'Critique check: not available' + (c.error ? ' · ' + c.error : '');
  const canRun = ['error', 'unavailable', 'not_run'].includes(c.status) && r.turns.length > 0;
  return `<p class="definition check-line">${esc(text)} ${canRun ? '<button class="rowlink" id="run-check" style="font-size:12px">Run critique check →</button>' : ''}</p>`;
}

function signals(r, a) {
  if (!r.turns.length) return `<section class="panel"><h2>This submission cannot be compared with AI output</h2>
    <p class="sub">Missing evidence is not evidence of poor engagement. Review completion is blocked until a transcript is supplied.</p>
    <p class="definition">“Missing transcript” is a coverage state, distinct from “No flags raised”.</p></section>`;

  if (!a.flags.length) {
    const good = substantiveBoxes(r);
    return `<section class="panel"><h2>Review the context before concluding</h2>
    <span class="pill green">No flags raised</span>
    <p class="sub" style="margin-top:12px">These checks may miss paraphrasing and subtle reasoning. No flags does not prove critical engagement.</p>
    ${good ? `<p class="definition">Replies the critique check rated substantive:</p>${good}` : ''}
    <button class="primary" data-tab="transcript">Read full transcript</button>${checkLine(r)}</section>`;
  }

  const f = a.flags.find(x => x.id === flagId) || a.flags[0];
  flagId = f.id;
  const d = r.decisions[f.id] || {decision: '', rationale: ''};
  const overlap = f.type === 'Text overlap', critique = !overlap;
  const options = ['Accept flag', 'Dismiss flag', 'Need more context'];
  const pill = overlap ? Math.round(f.score * 100) + '% phrase similarity' : VERDICT_LABELS[f.verdict];
  return `<div class="detail-grid"><div class="flaglist">${a.flags.map((x, i) => `<button class="flag ${x.id === f.id ? 'selected' : ''}" data-flag="${esc(x.id)}">
      <span class="pill ${r.decisions[x.id] ? 'green' : 'amber'}">${r.decisions[x.id] ? 'Decision saved' : 'Needs review'}</span>${x.origin === 'llm' ? ` <span class="pill blue">${originLabel(r)}</span>` : ''}
      <strong>${i + 1}. ${esc(x.type)}</strong>
      <small>${x.type === 'Text overlap' ? `Paragraph ${x.paragraph + 1} ↔ AI turn ${x.turn + 1}` : `Student turn ${x.turn + 1}`}</small></button>`).join('')}</div>
    <section class="panel"><h2>${esc(f.type)}</h2>
      <span class="pill amber">${pill}</span>${critique ? ` <span class="pill blue">${originLabel(r)}</span>` : ''}
      <p class="reason" style="margin-top:12px">${esc(f.reason)}</p>
      <div class="evidence"><article><h3>AI OUTPUT · TURN ${overlap ? f.turn + 1 : f.turn}</h3>${esc(f.source)}</article>
        <article><h3>${overlap ? `FINAL SUBMISSION · PARAGRAPH ${f.paragraph + 1}` : `STUDENT REPLY · TURN ${f.turn + 1}`}</h3>${esc(f.target)}</article></div>
      ${critique ? `<p class="quote">Quoted from the reply: “${esc(f.quote)}”</p>
        <p class="definition">${originLabel(r)} · ${esc(r.critique_check.model || '')} · rubric v${esc(r.critique_check.rubric_version)}. The quote was checked against the student's text. The model can be wrong, so read the full transcript before deciding.</p>` : ''}
      <button class="rowlink" id="context">${overlap ? 'View this turn in the full transcript →' : 'Read full transcript →'}</button>
      <div class="decision"><h3>Marker decision</h3>
        <label class="sr-only" for="decision">How should this flag be treated?</label>
        <select id="decision"><option value="">Select a decision</option>${options.map(x => `<option ${d.decision === x ? 'selected' : ''}>${x}</option>`).join('')}</select>
        <div id="decision-more" ${d.decision ? '' : 'hidden'}>
          <label for="rationale">Reason for this decision</label>
          <textarea id="rationale" placeholder="Explain what the evidence shows and why you made this decision.">${esc(d.rationale)}</textarea>
          <button class="primary" id="save-decision">Save decision</button></div>
        <p id="decision-error" class="form-error" role="alert"></p></div>${checkLine(r)}</section></div>
    ${substantiveReplies(r).length ? `<section class="panel"><h2>Replies rated substantive</h2><p class="definition">Context from the critique check. Read these alongside the flags.</p>${substantiveBoxes(r)}</section>` : ''}`;
}

function timeline(r, a) {
  const flagged = new Set(a.flags.map(f => f.turn));
  const size = t => Math.max(8, t.text.split(/\s+/).length);
  return `<div class="timeline" aria-label="Turn timeline">${r.turns.map((t, i) => `<button class="tl ${t.role === 'Student' ? 'student' : 'ai'} ${flagged.has(i) ? 'flagged' : ''}" style="flex:${size(t)}" data-turn="${i}" title="Turn ${i + 1} · ${t.role}${flagged.has(i) ? ' · part of a flag' : ''}" aria-label="Turn ${i + 1}, ${t.role}${flagged.has(i) ? ', part of a flag' : ''}"></button>`).join('')}</div>
    <p class="definition">Each block is one turn, sized by length. Green: student. Grey: AI. Amber outline: part of a flag. Select a block to jump to that turn.</p>`;
}

function transcript(r, a) {
  const f = a.flags.find(x => x.id === flagId) || a.flags[0];
  return `<section class="panel"><h2>Full interaction history</h2>
    ${r.turns.length ? timeline(r, a) : ''}
    <p class="definition">All supplied turns, in order. An exported conversation may still be incomplete.</p>
    ${r.turns.length ? r.turns.map((t, i) => `<article id="turn-${i}" class="turn ${t.role === 'Student' ? 'student' : ''} ${focusTurn === i ? 'target' : ''}"><h4>${t.role} · Turn ${i + 1}</h4><p>${esc(t.text)}</p></article>`).join('') : '<p>No transcript supplied.</p>'}
    ${f ? `<button class="primary" id="return-flag">Return to ${slug(f.type)} flag</button>` : ''}</section>`;
}

function finalText(r, a) {
  const c = r.contribution;
  const bar = r.turns.length ? `<section class="panel"><h2>Wording overlap with AI output</h2>
    <div class="bar" role="img" aria-label="${c.ai_percent}% of words match AI output"><span class="bar-ai" style="width:${c.ai_percent}%">${c.ai_percent >= 14 ? c.ai_percent + '% matches AI' : ''}</span><span class="bar-other" style="width:${c.other_percent}%">${c.other_percent >= 14 ? c.other_percent + '% other' : ''}</span></div>
    <p class="definition">${c.ai_words} of ${c.words} words sit inside five-word phrases that also appear in an AI turn (highlighted below). This shows wording overlap, not who wrote the text. Paraphrased AI text is not detected.</p></section>` : '';
  return bar + c.paragraphs.map((segs, i) => `<section class="panel"><h2>Final submission · Paragraph ${i + 1}</h2><p>${segs.map(x => x.ai ? `<mark class="ai">${esc(x.text)}</mark>` : esc(x.text)).join('')}</p></section>`).join('')
    + (r.turns.length ? '<button class="primary" data-tab="signals">Compare with AI output</button>' : '');
}

function notes(r, a) {
  const saved = Object.entries(r.decisions);
  const typeOf = id => (a.flags.find(f => f.id === id) || {type: id}).type;
  return `<section class="panel"><h2>Overall review note</h2>
    <label for="note">Marker note</label><textarea id="note" placeholder="Write your overall review…">${esc(r.note)}</textarea>
    <button class="primary" id="save-note" style="margin-top:12px">Save note</button></section>
    <section class="panel"><h2>Recorded decisions</h2>${saved.length ? saved.map(([id, d]) => `<article class="turn"><h4>${esc(typeOf(id))} · ${esc(d.decision)}</h4><p>${esc(d.rationale)}</p></article>`).join('') : '<p class="muted">No decisions saved yet.</p>'}</section>`;
}

function completePage() {
  const r = current, n = Object.keys(r.decisions).length;
  return `<div class="eyebrow">REVIEW STATUS</div><h1>Review complete</h1><p class="sub">${esc(r.student)} · ${esc(r.topic)}</p>
    <section class="panel"><h2>Review recorded</h2><span class="pill green">Reviewed</span>
      <ul class="reqs" style="margin-top:14px"><li>${n ? `${n} flag decision${n === 1 ? '' : 's'} resolved` : 'No flags to resolve'}</li><li>Overall marker note saved</li><li>No grade assigned</li></ul>
      <div class="actions" style="margin-bottom:0"><button class="secondary" id="export-review">Export review</button><button class="primary" id="back">View updated queue</button></div></section>`;
}

/* ---------- analysis method and guide ---------- */
function llmStatusText() {
  const l = llmInfo;
  if (l.mode === 'off') return 'Status: switched off. No critique flags are created.';
  if (l.mode === 'mock') return 'Status: simulated stand-in (a simple word pattern, not a language model).';
  if (l.key_present) return `Status: live checks are on (model ${esc(l.model)}). Saved results are reused, so the same text is not checked twice.`;
  return 'Status: no API key is set. Saved results are shown where they exist, and new submissions get no critique flags until a key is set.';
}

function method() {
  const card = (title, parts) => `<section class="panel"><h2>${title}</h2>${parts.map(([label, html]) => `<div class="m-label">${label}</div>${html}`).join('')}</section>`;
  return `<div class="eyebrow">TRANSPARENCY</div><h1>Analysis method</h1>
    <p class="sub">A language model rates how each student responded to the AI. The marker makes every decision, and nothing is graded.</p>
    <section class="panel"><h2>How a submission is checked</h2>
      <div class="pipeline"><div><b>1</b>OpenAI critique check<small>Rates every student reply</small></div><span>→</span>
        <div><b>2</b>Wording comparison<small>Final text against the AI turns</small></div><span>→</span>
        <div><b>3</b>The marker decides<small>Accept, dismiss or ask for more context</small></div></div></section>
    <div class="method-grid">
      ${card('01 · Critique check (OpenAI)', [
        ['What it checks', '<p>An OpenAI model reads every student reply that follows an AI answer, together with that answer, and rates the reply as <strong>substantive</strong> (engages with specific content, for example by questioning a claim, asking for evidence or applying the answer to the student\'s own situation), <strong>generic</strong> (keeps the conversation going without evaluating, for example “expand on that”) or <strong>blind acceptance</strong> (accepts or thanks without evaluating).</p>'],
        ['What becomes a flag', '<p>Generic and blind acceptance replies. Each flag is labelled LLM-assisted and carries a quote from the student\'s own words. Replies rated substantive are shown to the marker as context.</p>'],
        ['Safeguards', '<p>Every quote is checked against the student\'s text, and a flag whose quote cannot be found is rejected. Student text is treated as data, not instructions. Results are saved with the model and rubric version used.</p>'],
        ['Limits', `<p class="sub">The model can be wrong, sees only the text supplied, and cannot tell whether a student used AI to write a reply. If the check is unavailable, no critique flags are created for that submission and the review page says why.</p><p class="definition">${llmStatusText()}</p>`]])}
      ${card('02 · Text overlap', [
        ['What it checks', '<p>The one check the model does not do. Each paragraph of the final submission is compared with every AI turn. Text is lowercased, punctuation is removed, and consecutive five-word phrases are compared.</p><div class="formula">Jaccard = shared phrases ÷ distinct phrases in either text</div>'],
        ['What becomes a flag', '<p>A paragraph whose best-matching AI turn reaches the standard review threshold, shown side by side. The Final submission tab also shows how many words match, with those words highlighted.</p>'],
        ['Limits', '<p class="sub">It measures matching wording, not who wrote the text. Paraphrased text is not detected, and text shorter than five words scores zero.</p>']])}
    </div>
    <section class="panel"><h2>What this tool does not do</h2>
      <p class="sub" style="margin-bottom:0">It does not grade work, decide whether a student used AI, or make an academic-integrity finding. Flags are reasons to look closer, and the marker decides what each one means.</p></section>`;
}

function guide() {
  const steps = [
    ['Open the review queue', 'Choose a submission. The Flags column shows how many places to look at more closely.'],
    ['Check the evidence', 'Compare each flag with the AI turn it relates to, then read the full transcript for context.'],
    ['Record a decision', 'Choose Accept flag, Dismiss flag or Need more context, and give a reason.'],
    ['Add an overall note', 'Use Marker notes to record your interpretation and any follow-up.'],
    ['Complete the review', 'Decide every flag (none left as Need more context), save the note, then select Complete review. Export review saves a readable PDF report.'],
    ['Handle exceptions', 'A missing transcript blocks completion until the student supplies it. No flags does not prove strong engagement, so still read the transcript.']
  ];
  return `<div class="eyebrow">START HERE</div><h1>Walk through a review</h1><p class="sub">Follow these steps to complete a review.</p>
    <section class="panel"><h2>Suggested steps</h2>
      ${steps.map(([a, b], i) => `<div class="step"><b>${pad(i + 1)}</b><div><strong>${a}</strong><p>${b}</p></div></div>`).join('')}
      <div class="actions" style="margin:18px 0 0"><button class="secondary" id="go-queue">Open review queue</button></div></section>`;
}

/* ---------- dialogs ---------- */
function modal(opts) {
  $('modal-body').innerHTML = `<div class="modal-head"><div>${opts.eyebrow ? `<div class="eyebrow">${opts.eyebrow}</div>` : ''}<h2>${opts.title}</h2></div><button class="close" id="close-modal" aria-label="Close dialog">×</button></div>${opts.body}`;
  $('modal').showModal();
  $('close-modal').onclick = () => $('modal').close();
}

function requirements(r) {
  const flags = r.analysis.flags, d = r.decisions;
  return [
    ['A supplied transcript', r.turns.length > 0],
    ['A saved overall marker note', r.note.trim().length > 0],
    ['A decision and reason for every flag', flags.every(f => d[f.id])],
    ['No flag left as “Need more context”', flags.every(f => !(d[f.id] && d[f.id].decision === 'Need more context'))]
  ];
}

function blockedDialog() {
  modal({eyebrow: 'VALIDATION', title: 'Review is not complete', body: `<p class="sub">Resolve the missing requirements before completing a review.</p>
    <h3>Completion requirements</h3>
    <ul class="reqs">${requirements(current).map(([t, ok]) => `<li class="${ok ? 'ok' : 'no'}">${ok ? '✓' : '✗'} ${t}</li>`).join('')}</ul>
    <div class="note-amber">A flag can be accepted or dismissed. “Need more context” remains unresolved.</div>
    <div class="actions"><button class="primary" id="m-flags">Continue reviewing flags</button><button class="secondary" id="m-notes">Go to marker notes</button></div>`});
  $('m-flags').onclick = () => { $('modal').close(); tab = 'signals'; render(); };
  $('m-notes').onclick = () => { $('modal').close(); tab = 'notes'; render(); };
}

/* ---------- actions that change data (each one is a server call) ---------- */
async function saveDecision() {
  const decision = $('decision').value, rationale = $('rationale').value.trim();
  if (!decision || !rationale) { $('decision-error').textContent = 'Select a decision and enter a reason before saving.'; return; }
  await api(`/api/submissions/${encodeURIComponent(current.id)}/flags/${encodeURIComponent(flagId)}/decision`,
    {method: 'PUT', body: JSON.stringify({decision, rationale})});
  current.decisions[flagId] = {decision, rationale};
  current.status = 'In progress';
  render();
  toast('Decision saved.');
}

async function saveNote() {
  const note = $('note').value.trim();
  await api(`/api/submissions/${encodeURIComponent(current.id)}/note`, {method: 'PUT', body: JSON.stringify({note})});
  current.note = note;
  current.status = 'In progress';
  render();
  toast('Marker note saved.');
}

async function complete() {
  try {
    await api(`/api/submissions/${encodeURIComponent(current.id)}/complete`, {method: 'POST', body: '{}'});
  } catch (err) {
    blockedDialog();
    return;
  }
  current.status = 'Reviewed';
  show('complete');
}

async function runCheck() {
  $('run-check').disabled = true;
  try {
    current = await api(`/api/submissions/${encodeURIComponent(current.id)}/critique-check`, {method: 'POST', body: '{}'});
    render();
    toast('Critique check complete.');
  } catch (err) {
    render();
    toast(err.message);
  }
}

function goTurn(i) {
  focusTurn = i; tab = 'transcript'; render();
  const el = $('turn-' + i);
  if (el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
}

function bind() {
  document.querySelectorAll('[data-open]').forEach(b => b.onclick = guard(() => openRecord(b.dataset.open)));
  document.querySelectorAll('[data-tab]').forEach(b => b.onclick = () => { tab = b.dataset.tab; render(); });
  document.querySelectorAll('[data-flag]').forEach(b => b.onclick = () => { flagId = b.dataset.flag; render(); });
  const on = (id, fn) => { if ($(id)) $(id).onclick = fn; };
  on('back', guard(goQueue));
  on('go-queue', guard(goQueue));
  on('context', () => goTurn(current.analysis.flags.find(x => x.id === flagId).turn));
  on('return-flag', () => { tab = 'signals'; render(); });
  on('run-check', guard(runCheck));
  document.querySelectorAll('.tl[data-turn]').forEach(b => b.onclick = () => goTurn(Number(b.dataset.turn)));
  on('save-decision', guard(saveDecision));
  on('save-note', guard(saveNote));
  on('complete', guard(complete));
  on('export-review', () => { window.open('/api/submissions/' + encodeURIComponent(current.id) + '/export', '_blank'); });
  on('export-queue', () => { location.href = '/api/queue/export'; });
  if ($('decision')) $('decision').onchange = e => { $('decision-more').hidden = !e.target.value; };
  if ($('search')) $('search').oninput = e => {
    query = e.target.value;
    $('rows').innerHTML = rows();
    document.querySelectorAll('[data-open]').forEach(b => b.onclick = guard(() => openRecord(b.dataset.open)));
  };
  if ($('filter')) $('filter').onchange = e => { filter = e.target.value; render(); };
}

document.querySelectorAll('[data-view]').forEach(b => b.onclick = guard(async () => {
  if (b.dataset.view === 'queue') await loadQueue();
  show(b.dataset.view);
}));

loadQueue().then(render).catch(err => { $('main').innerHTML = `<div class="panel empty"><h2>Could not load the queue</h2><p class="sub">${err.message.replace(/[<>&]/g, '')}</p></div>`; });
