'use strict';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

function toast(text) {
  $('toast').textContent = text;
  $('toast').style.display = 'block';
  setTimeout(() => { $('toast').style.display = 'none'; }, 3500);
}

async function api(path, options = {}) {
  const res = await fetch(path, {credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, ...options});
  let data = null;
  try { data = await res.json(); } catch (e) { /* no JSON body */ }
  if (res.status === 401) { location.href = '/student/login'; throw new Error('Please sign in again.'); }
  if (!res.ok) throw new Error((data && data.error) || 'Request failed (' + res.status + ').');
  return data;
}

function formatTime(iso) { return iso.slice(0, 16).replace('T', ' ') + ' UTC'; }

async function loadList() {
  const d = await api('/api/student/submissions');
  $('my-rows').innerHTML = d.submissions.map(s => `<tr>
      <td><strong>${esc(s.ref)}</strong></td><td>${esc(s.topic)}</td><td>${esc(formatTime(s.submitted_at))}</td>
      <td><span class="pill green">Received</span></td>
      <td>${s.turn_count ? `${s.turn_count} turns supplied`
        : `<span class="pill amber">Missing</span> <button class="rowlink" data-add="${esc(s.ref)}">Add transcript →</button>`}</td>
    </tr>`).join('') || '<tr><td colspan="5" class="empty">You have not submitted any work yet.</td></tr>';
  document.querySelectorAll('[data-add]').forEach(b => b.onclick = () => transcriptDialog(b.dataset.add));
}

// Load a .txt file into a textarea (client-side only; the server still validates the text).
function wireFile(fileId, textId) {
  $(fileId).onchange = async e => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 200000) { $('submit-error').textContent = 'That file is too large. Use a .txt file under 200 KB.'; e.target.value = ''; return; }
    $(textId).value = await file.text();
    $('submit-error').textContent = '';
  };
}
wireFile('final-file', 'final-text');
wireFile('transcript-file', 'transcript');

$('submit-form').onsubmit = async e => {
  e.preventDefault();
  $('submit-error').textContent = '';
  $('submit-btn').disabled = true;
  try {
    const res = await api('/api/student/submissions', {method: 'POST', body: JSON.stringify({
      topic: $('topic').value, final_text: $('final-text').value, transcript: $('transcript').value,
      no_transcript: $('no-transcript').checked})});
    $('submit-form').reset();
    $('received').hidden = false;
    $('received').textContent = 'Submission received. Your reference is ' + res.ref + '.';
    window.scrollTo(0, 0);
    await loadList();
  } catch (err) {
    $('submit-error').textContent = err.message;
  } finally {
    $('submit-btn').disabled = false;
  }
};

function transcriptDialog(ref) {
  $('modal-body').innerHTML = `<div class="modal-head"><h2>Add AI interaction history</h2><button class="close" id="close-modal" aria-label="Close dialog">×</button></div>
    <p class="definition">Submission ${esc(ref)}. Begin each turn with Student: or AI:. A transcript can only be added once.</p>
    <form id="transcript-form"><div class="form-field"><label for="modal-transcript">AI interaction history</label>
    <textarea id="modal-transcript" maxlength="30000" required></textarea></div>
    <button class="primary" type="submit">Add transcript</button><p id="modal-error" class="form-error" role="alert"></p></form>`;
  $('modal').showModal();
  $('close-modal').onclick = () => $('modal').close();
  $('transcript-form').onsubmit = async e => {
    e.preventDefault();
    try {
      await api('/api/student/submissions/' + encodeURIComponent(ref) + '/transcript',
        {method: 'POST', body: JSON.stringify({transcript: $('modal-transcript').value})});
      $('modal').close();
      toast('Transcript added.');
      await loadList();
    } catch (err) { $('modal-error').textContent = err.message; }
  };
}

loadList().catch(err => { $('my-rows').innerHTML = `<tr><td colspan="5" class="empty">${esc(err.message)}</td></tr>`; });
