/* ═══════════════════════════════════════════════════
   PRISM — Counselor Frontend Controller
   Dashboard + Manage (CRUD) + Predictor + Drawer
   ═══════════════════════════════════════════════════ */

let students = [];
let cohortAudit = {};
let targets = {};
let currentStudent = null;
let simSubjects = [];
let editingId = null;

const BOARD_SUBJECTS = {
  "CBSE": [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "Informatics Practices", "English Core", "Hindi Core", "Economics",
    "Accountancy", "Business Studies", "Entrepreneurship", "History",
    "Political Science", "Geography", "Sociology", "Psychology",
    "Physical Education", "Fine Arts"
  ],
  "ICSE": [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "Elective English", "Accounts", "Commerce", "Economics", "Business Studies",
    "History & Civics", "Political Science", "Geography", "Sociology",
    "Psychology", "Art", "Physical Education"
  ],
  "IB": [
    "Mathematics Analysis & Approaches (HL/SL)",
    "Mathematics Applications & Interpretation (HL/SL)",
    "Physics (HL/SL)", "Chemistry (HL/SL)", "Biology (HL/SL)",
    "Computer Science (HL/SL)", "English A Literature (HL/SL)",
    "Economics (HL/SL)", "Business Management (HL/SL)", "History (HL/SL)",
    "Geography (HL/SL)", "Psychology (HL/SL)", "Visual Arts (HL/SL)"
  ],
  "A-Levels": [
    "Mathematics", "Further Mathematics", "Physics", "Chemistry", "Biology",
    "Computer Science", "English Language", "English Literature", "Economics",
    "Accounting", "Business", "History", "Geography", "Psychology", "Art & Design"
  ],
  "State Board": [
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "English", "Regional Language", "Economics", "Accountancy",
    "Organization of Commerce", "History", "Political Science", "Geography"
  ]
};

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    const [sRes, aRes, tRes] = await Promise.all([
      fetch('/api/students'),
      fetch('/api/evaluate_cohort'),
      fetch('/api/targets')
    ]);
    students = await sRes.json();
    cohortAudit = await aRes.json();
    targets = await tRes.json();
    renderDashboard();
    initManageForm();

    const boardSelect = document.getElementById('mf-board');
    if (boardSelect) {
      boardSelect.addEventListener('change', updateManageSubjectsGrid);
    }
  } catch (e) {
    document.getElementById('student-rows').innerHTML =
      '<div class="loading-row" style="color:var(--red)">✕ failed to connect to engine</div>';
  }
}

async function refreshData() {
  const [sRes, aRes] = await Promise.all([
    fetch('/api/students'),
    fetch('/api/evaluate_cohort')
  ]);
  students = await sRes.json();
  cohortAudit = await aRes.json();
  renderDashboard();
  renderManageList();
}

// ── View switching ──
function switchView(v) {
  ['dashboard', 'manage', 'predictor'].forEach(id => {
    document.getElementById(`view-${id}`).classList.toggle('hidden', id !== v);
    document.getElementById(`tab-${id === 'manage' ? 'manage' : id === 'dashboard' ? 'dash' : 'pred'}`).classList.toggle('active', id === v);
  });
  if (v === 'manage') renderManageList();
}

// ══════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════

function renderDashboard() {
  let pass = 0, crit = 0, gaps = 0;
  students.forEach(s => {
    const a = cohortAudit[s.id]; if (!a) return;
    let ok = true;
    for (const t in a.targets) {
      const r = a.targets[t];
      if (!r.compliant) { ok = false; gaps += r.gaps.length; }
      if (r.urgency_score >= 35) crit++;
    }
    if (ok) pass++;
  });

  animateNum('m-cohort', students.length);
  animateNum('m-pass', pass);
  animateNum('m-risk', crit);
  animateNum('m-gaps', gaps);

  document.getElementById('dash-subtitle').textContent =
    `${students.length} students · ${Object.keys(targets).length} target pathways · real-time audit`;

  const rows = document.getElementById('student-rows');
  rows.innerHTML = '';

  if (students.length === 0) {
    rows.innerHTML = '<div class="loading-row">no students yet — go to manage tab to add</div>';
    return;
  }

  students.forEach(s => {
    const a = cohortAudit[s.id]; if (!a) return;
    let maxUrg = 0, names = [], hasGap = false;
    for (const t in a.targets) {
      const r = a.targets[t];
      names.push(r.target_name);
      maxUrg = Math.max(maxUrg, r.urgency_score);
      if (!r.compliant) hasGap = true;
    }

    const filled = Math.round((Math.min(maxUrg, 100) / 100) * 8);
    const empty = 8 - filled;
    let riskColor, markerClass, statusText, statusClass;
    if (!hasGap) {
      riskColor = 'var(--green)'; markerClass = 'nm-pass'; statusText = 'pass'; statusClass = 'st-pass';
    } else if (maxUrg >= 35) {
      riskColor = 'var(--red)'; markerClass = 'nm-crit'; statusText = 'critical'; statusClass = 'st-crit';
    } else {
      riskColor = 'var(--amber)'; markerClass = 'nm-warn'; statusText = 'warning'; statusClass = 'st-warn';
    }
    const blocks = `<span style="color:${riskColor}">${'█'.repeat(filled)}</span><span style="color:var(--border)">${'░'.repeat(empty)}</span>`;

    const row = document.createElement('div');
    row.className = 'stu-row';
    row.onclick = () => openDrawer(s.id);
    row.innerHTML = `
      <div class="col-name">
        <div class="name-marker ${markerClass}"></div>
        <div><div class="name-text">${s.name}</div><div class="name-id">${s.id}</div></div>
      </div>
      <div><div class="col-board">${s.board}</div><div class="col-board-class">class ${s.class_level}</div></div>
      <div class="col-targets">${names.join(' · ')}</div>
      <div class="col-risk">
        <div class="risk-blocks">${blocks}</div>
        <div class="risk-pct" style="color:${riskColor}">${maxUrg}%</div>
      </div>
      <div class="status-tag ${statusClass}">${statusText}</div>
    `;
    rows.appendChild(row);
  });
}

function animateNum(id, to) {
  const el = document.getElementById(id);
  const dur = 500, start = performance.now();
  (function tick(now) {
    const p = Math.min((now - start) / dur, 1);
    el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  })(start);
}

// ══════════════════════════════════════════════
//  MANAGE — CRUD
// ══════════════════════════════════════════════

function updateManageSubjectsGrid() {
  const board = document.getElementById('mf-board').value;
  const subjects = BOARD_SUBJECTS[board] || BOARD_SUBJECTS["CBSE"];
  
  // Student subjects checkboxes (student form)
  const subEl = document.getElementById('mf-subjects');
  subEl.innerHTML = '';
  subjects.forEach(sub => {
    const lbl = document.createElement('label');
    lbl.className = 'sc-label';
    lbl.innerHTML = `<input type="checkbox" value="${sub}" />${sub}`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
    subEl.appendChild(lbl);
  });

  // Compulsory subject checkboxes (target form)
  const compEl = document.getElementById('mt-compulsory');
  compEl.innerHTML = '';
  subjects.forEach(sub => {
    const lbl = document.createElement('label');
    lbl.className = 'sc-label';
    lbl.innerHTML = `<input type="checkbox" value="${sub}" />${sub}`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
    compEl.appendChild(lbl);
  });
}

function initManageForm() {
  updateManageSubjectsGrid();

  // Populate target checkboxes (student form)
  refreshStudentTargetCheckboxes();
}

function refreshStudentTargetCheckboxes() {
  const trgEl = document.getElementById('mf-targets');
  trgEl.innerHTML = '';
  for (const tid in targets) {
    const lbl = document.createElement('label');
    lbl.className = 'sc-label';
    lbl.innerHTML = `<input type="checkbox" value="${tid}" /><span>${targets[tid].name}</span>`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
    trgEl.appendChild(lbl);
  }
}

function renderManageList() {
  // Students List
  const el = document.getElementById('manage-student-list');
  el.innerHTML = '';
  if (students.length === 0) {
    el.innerHTML = '<div class="loading-row">no students yet</div>';
  } else {
    students.forEach(s => {
      const row = document.createElement('div');
      row.className = 'manage-stu-row';
      row.innerHTML = `
        <div class="msr-info">
          <span class="msr-name">${s.name}</span>
          <span class="msr-meta">${s.id} · ${s.board} · class ${s.class_level}</span>
        </div>
        <div class="msr-actions">
          <button class="btn-edit" onclick="editStudent('${s.id}')">edit</button>
          <button class="btn-delete" onclick="deleteStudent('${s.id}', '${s.name}')">delete</button>
        </div>
      `;
      el.appendChild(row);
    });
  }

  // Targets List
  const tel = document.getElementById('manage-target-list');
  tel.innerHTML = '';
  if (Object.keys(targets).length === 0) {
    tel.innerHTML = '<div class="loading-row">no target pathways yet</div>';
  } else {
    for (const tid in targets) {
      const t = targets[tid];
      const row = document.createElement('div');
      row.className = 'manage-stu-row';
      row.innerHTML = `
        <div class="msr-info">
          <span class="msr-name">${t.name}</span>
          <span class="msr-meta">${tid} · ${t.university || 'No university'} · Track: ${t.track} · portfolio: Tier ${t.portfolio_tier}</span>
        </div>
        <div class="msr-actions">
          <button class="btn-delete" onclick="deleteTarget('${tid}', '${t.name}')">delete</button>
        </div>
      `;
      tel.appendChild(row);
    }
  }
}

async function submitTargetForm(e) {
  e.preventDefault();
  const name = document.getElementById('mt-name').value.trim();
  const university = document.getElementById('mt-uni').value.trim();
  const track = document.getElementById('mt-track').value;
  const portfolio_tier = parseInt(document.getElementById('mt-portfolio').value);

  const checkedComp = document.querySelectorAll('#mt-compulsory input:checked');
  const compSubjects = [...checkedComp].map(cb => cb.value);

  const subject_prerequisites = compSubjects.map(sub => ({
    subject: sub,
    level: "compulsory",
    notes: `Must study ${sub}`
  }));

  const payload = {
    name,
    university,
    track,
    portfolio_tier,
    subject_prerequisites
  };

  const btn = document.getElementById('mt-submit');
  btn.disabled = true;
  btn.textContent = 'saving…';

  try {
    const res = await fetch('/api/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const tData = await res.json();
      targets[tData.id] = tData;
      document.getElementById('target-form').reset();
      document.querySelectorAll('#mt-compulsory input').forEach(cb => {
        cb.checked = false;
        cb.parentElement.classList.remove('checked');
      });
      refreshStudentTargetCheckboxes();
      renderManageList();
      await refreshData();
    }
  } catch (err) {
    alert('Failed to add pathway');
  } finally {
    btn.disabled = false;
    btn.textContent = 'add pathway →';
  }
}

async function deleteTarget(tid, name) {
  if (!confirm(`Delete pathway "${name}"? Existing students targets might get decoupled.`)) return;
  try {
    const res = await fetch(`/api/targets/${tid}`, { method: 'DELETE' });
    if (res.ok) {
      delete targets[tid];
      refreshStudentTargetCheckboxes();
      renderManageList();
      await refreshData();
    }
  } catch (err) {
    alert('Failed to delete pathway');
  }
}

function addPortfolioRow(activity = '', desc = '', tier = 3) {
  const list = document.getElementById('mf-portfolio-list');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.innerHTML = `
    <input type="text" placeholder="activity name" class="pf-activity" value="${activity}" />
    <input type="text" placeholder="description" class="pf-desc" value="${desc}" />
    <select class="pf-tier"><option value="1" ${tier === 1 ? 'selected' : ''}>Tier 1</option><option value="2" ${tier === 2 ? 'selected' : ''}>Tier 2</option><option value="3" ${tier === 3 ? 'selected' : ''}>Tier 3</option></select>
    <button type="button" class="btn-delete-sm" onclick="this.parentElement.remove()">✕</button>
  `;
  list.appendChild(row);
}

function getFormData() {
  const subjectCbs = document.querySelectorAll('#mf-subjects input:checked');
  const targetCbs = document.querySelectorAll('#mf-targets input:checked');
  const boardSubjects = [...subjectCbs].map(cb => cb.value);
  const tgts = [...targetCbs].map(cb => cb.value);

  const cuetRaw = document.getElementById('mf-cuet').value.trim();
  const cuetSubjects = cuetRaw ? cuetRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  const grades = {};
  const g10 = document.getElementById('mf-g10').value.trim();
  const g11 = document.getElementById('mf-g11').value.trim();
  const gexp = document.getElementById('mf-gexp').value.trim();
  if (g10) grades.class_10_aggregate = g10;
  if (g11) grades.class_11_aggregate = g11;
  if (gexp) grades.current_expected_board = gexp;

  const tests = {};
  const sat = document.getElementById('mf-sat').value;
  const ap = document.getElementById('mf-ap').value;
  if (sat) tests.SAT = parseInt(sat);
  if (ap) tests.AP_CALCULUS_BC = parseInt(ap);

  const portfolio = [];
  document.querySelectorAll('.portfolio-row').forEach(row => {
    const act = row.querySelector('.pf-activity').value.trim();
    const d = row.querySelector('.pf-desc').value.trim();
    const t = parseInt(row.querySelector('.pf-tier').value);
    if (act) portfolio.push({ activity: act, description: d, tier: t });
  });

  return {
    name: document.getElementById('mf-name').value.trim(),
    board: document.getElementById('mf-board').value,
    class_level: parseInt(document.getElementById('mf-class').value),
    board_subjects: boardSubjects,
    cuet_subjects: cuetSubjects,
    grades,
    standardized_tests: tests,
    portfolio,
    targets: tgts
  };
}

async function submitStudentForm(e) {
  e.preventDefault();
  const data = getFormData();
  if (!data.name) return alert('Name is required');
  if (data.board_subjects.length === 0) return alert('Select at least one subject');

  const btn = document.getElementById('mf-submit');
  btn.disabled = true;
  btn.textContent = 'saving…';

  try {
    if (editingId) {
      await fetch(`/api/students/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } else {
      await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    }
    resetManageForm();
    await refreshData();
  } catch (err) {
    alert('Save failed');
  } finally {
    btn.disabled = false;
    btn.textContent = editingId ? 'save changes →' : 'add student →';
  }
}

function editStudent(sid) {
  const s = students.find(st => st.id === sid);
  if (!s) return;
  editingId = sid;

  document.getElementById('manage-form-title').textContent = `editing: ${s.name}`;
  document.getElementById('mf-submit').textContent = 'save changes →';
  document.getElementById('mf-cancel').style.display = '';
  document.getElementById('mf-id').value = sid;
  document.getElementById('mf-name').value = s.name;
  document.getElementById('mf-board').value = s.board;
  updateManageSubjectsGrid();
  document.getElementById('mf-class').value = s.class_level;

  // Check subjects
  document.querySelectorAll('#mf-subjects input').forEach(cb => {
    const checked = (s.board_subjects || []).includes(cb.value);
    cb.checked = checked;
    cb.parentElement.classList.toggle('checked', checked);
  });

  // Check targets
  document.querySelectorAll('#mf-targets input').forEach(cb => {
    const checked = (s.targets || []).includes(cb.value);
    cb.checked = checked;
    cb.parentElement.classList.toggle('checked', checked);
  });

  document.getElementById('mf-cuet').value = (s.cuet_subjects || []).join(', ');
  document.getElementById('mf-g10').value = s.grades?.class_10_aggregate || '';
  document.getElementById('mf-g11').value = s.grades?.class_11_aggregate || '';
  document.getElementById('mf-gexp').value = s.grades?.current_expected_board || '';
  document.getElementById('mf-sat').value = s.standardized_tests?.SAT || '';
  document.getElementById('mf-ap').value = s.standardized_tests?.AP_CALCULUS_BC || '';

  // Portfolio
  document.getElementById('mf-portfolio-list').innerHTML = '';
  (s.portfolio || []).forEach(p => addPortfolioRow(p.activity, p.description, p.tier));

  // Scroll to form
  document.getElementById('manage-form').scrollIntoView({ behavior: 'smooth' });
}

function resetManageForm() {
  editingId = null;
  document.getElementById('manage-form-title').textContent = 'add new student';
  document.getElementById('mf-submit').textContent = 'add student →';
  document.getElementById('mf-cancel').style.display = 'none';
  document.getElementById('manage-form').reset();
  updateManageSubjectsGrid();
  document.getElementById('mf-portfolio-list').innerHTML = '';
  document.querySelectorAll('#mf-subjects input, #mf-targets input').forEach(cb => {
    cb.checked = false;
    cb.parentElement.classList.remove('checked');
  });
}

async function deleteStudent(sid, name) {
  if (!confirm(`Delete ${name}? This cannot be undone.`)) return;
  await fetch(`/api/students/${sid}`, { method: 'DELETE' });
  await refreshData();
}

// ══════════════════════════════════════════════
//  DRAWER
// ══════════════════════════════════════════════

async function openDrawer(sid) {
  currentStudent = students.find(s => s.id === sid);
  if (!currentStudent) return;
  simSubjects = [...(currentStudent.board_subjects || [])];

  const initials = currentStudent.name.split(' ').map(n => n[0]).join('');
  document.getElementById('d-initials').textContent = initials;
  document.getElementById('d-name').textContent = currentStudent.name;
  document.getElementById('d-detail').textContent =
    `${currentStudent.board} · class ${currentStudent.class_level} · ${currentStudent.board_subjects.join(', ')}`;

  document.getElementById('drawer-backdrop').classList.remove('hidden');
  document.getElementById('drawer').classList.remove('hidden');
  await renderCompliance(sid);
  renderSimChecks();
  switchDTab('gaps');
}

function closeDrawer() {
  document.getElementById('drawer-backdrop').classList.add('hidden');
  document.getElementById('drawer').classList.add('hidden');
  currentStudent = null;
}

function switchDTab(t) {
  ['gaps', 'rem', 'sim'].forEach(k => {
    document.getElementById(`dtab-${k}`).classList.toggle('active', k === t);
    document.getElementById(`d-${k}`).classList.toggle('hidden', k !== t);
  });
}

async function renderCompliance(sid, subs = null) {
  const body = { student_id: sid };
  if (subs) body.simulated_subjects = subs;
  const res = await fetch('/api/evaluate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  const audit = await res.json();

  const gEl = document.getElementById('d-gaps');
  const rEl = document.getElementById('d-rem');
  gEl.innerHTML = ''; rEl.innerHTML = '';

  for (const tid in audit.targets) {
    const t = audit.targets[tid];

    // Gaps
    const gb = document.createElement('div'); gb.className = 'target-block';
    gb.innerHTML = `<div class="tb-header"><span class="tb-name">${t.target_name}</span><span class="tb-badge ${t.compliant ? 'tb-pass' : 'tb-fail'}">${t.compliant ? 'pass' : t.gaps.length + ' gap' + (t.gaps.length > 1 ? 's' : '')}</span></div>`;
    const gbody = document.createElement('div'); gbody.className = 'tb-body';
    if (t.compliant) {
      gbody.innerHTML = '<div class="tb-ok">✔ all requirements verified</div>';
    } else {
      t.gaps.forEach(g => {
        const ge = document.createElement('div'); ge.className = 'gap-entry';
        ge.innerHTML = `<div class="ge-title">${g.subject || '—'}: ${g.description}</div><div class="ge-meta"><strong>citation:</strong> ${g.citation}<br><strong>verified:</strong> ${g.last_verified} · <strong>severity:</strong> ${g.severity}</div>`;
        gbody.appendChild(ge);
      });
    }
    gb.appendChild(gbody); gEl.appendChild(gb);

    // Remediations
    const rb = document.createElement('div'); rb.className = 'target-block';
    rb.innerHTML = `<div class="tb-header"><span class="tb-name">${t.target_name}</span></div>`;
    const rbody = document.createElement('div'); rbody.className = 'tb-body';
    if (t.compliant) {
      rbody.innerHTML = '<div class="rem-ok">✔ no remediation needed</div>';
    } else if (!t.remediations || t.remediations.length === 0) {
      rbody.innerHTML = '<div style="font-size:0.75rem;color:var(--text-3)">no automated paths matched</div>';
    } else {
      t.remediations.forEach((r, i) => {
        const fc = r.feasibility === 'HIGH' ? 'rf-high' : r.feasibility === 'MEDIUM' ? 'rf-med' : 'rf-low';
        const re = document.createElement('div'); re.className = 'rem-entry';
        re.innerHTML = `<div class="re-header"><span class="re-num">option ${i + 1}</span><span class="re-feas ${fc}">${r.feasibility}</span></div><div class="re-text">${r.remediation}</div><div class="re-detail"><strong>action:</strong> ${r.action_item}<br><strong>reasoning:</strong> ${r.reasoning}</div>`;
        rbody.appendChild(re);
      });
    }
    rb.appendChild(rbody); rEl.appendChild(rb);
  }
}

// ── Simulator ──
function renderSimChecks() {
  const c = document.getElementById('sim-checks'); c.innerHTML = '';
  SUBJECTS.forEach(sub => {
    const on = simSubjects.includes(sub);
    const lbl = document.createElement('label');
    lbl.className = `sc-label${on ? ' checked' : ''}`;
    lbl.innerHTML = `<input type="checkbox" ${on ? 'checked' : ''} />${sub}`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => {
      if (cb.checked) { if (!simSubjects.includes(sub)) simSubjects.push(sub); lbl.classList.add('checked'); }
      else { simSubjects = simSubjects.filter(s => s !== sub); lbl.classList.remove('checked'); }
    });
    c.appendChild(lbl);
  });
}

async function runSim() {
  if (!currentStudent) return;
  document.getElementById('d-detail').textContent = `${currentStudent.board} · class ${currentStudent.class_level} · SIM: ${simSubjects.join(', ')}`;
  await renderCompliance(currentStudent.id, simSubjects);
  switchDTab('gaps');
}

async function resetSim() {
  if (!currentStudent) return;
  simSubjects = [...(currentStudent.board_subjects || [])];
  renderSimChecks();
  document.getElementById('d-detail').textContent = `${currentStudent.board} · class ${currentStudent.class_level} · ${currentStudent.board_subjects.join(', ')}`;
  await renderCompliance(currentStudent.id);
  switchDTab('gaps');
}

// ══════════════════════════════════════════════
//  PREDICTOR
// ══════════════════════════════════════════════

async function runPredictor(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-predict');
  btn.disabled = true; btn.textContent = 'running…';
  try {
    const res = await fetch('/api/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject: document.getElementById('f-subject').value,
        aim: document.getElementById('f-aim').value,
        country: document.getElementById('f-country').value,
        tariff: parseFloat(document.getElementById('f-tariff').value),
        nss: parseFloat(document.getElementById('f-nss').value),
        tef: document.getElementById('f-tef').value,
        tef_exp: document.getElementById('f-tef').value,
        tef_out: document.getElementById('f-tef').value,
        foundation: document.getElementById('f-foundation').checked ? 1 : 0,
        honours: document.getElementById('f-honours').checked ? 1 : 0,
        sandwich: document.getElementById('f-sandwich').checked ? 1 : 0,
        yearabroad: document.getElementById('f-yearabroad').checked ? 1 : 0
      })
    });
    const d = await res.json(); const p = d.predictions;
    document.getElementById('r-salary').textContent = p.salary != null ? `£${Math.round(p.salary).toLocaleString('en-GB')}` : '—';
    document.getElementById('r-continuation').textContent = p.continuation != null ? `${p.continuation.toFixed(1)}%` : '—';
    document.getElementById('r-employment').textContent = p.employment != null ? `${p.employment.toFixed(1)}%` : '—';
    document.getElementById('pred-empty').classList.add('hidden');
    document.getElementById('pred-results').classList.remove('hidden');
  } catch (err) { console.error(err); }
  finally { btn.disabled = false; btn.textContent = 'run prediction →'; }
}

// ══════════════════════════════════════════════
//  AUTOCOMPLETE SEARCH
// ══════════════════════════════════════════════

let selectedUniversity = "";

async function searchUniversities(val) {
  const container = document.getElementById("mt-uni-results");
  if (!val.trim()) {
    container.classList.add("hidden");
    return;
  }

  try {
    const res = await fetch(`/api/search_unis?q=${encodeURIComponent(val)}`);
    const list = await res.json();
    if (list.length === 0) {
      container.classList.add("hidden");
      return;
    }

    container.innerHTML = "";
    container.classList.remove("hidden");
    list.forEach(uni => {
      const div = document.createElement("div");
      div.className = "autocomplete-suggestion";
      div.textContent = uni;
      div.onclick = () => {
        document.getElementById("mt-uni").value = uni;
        selectedUniversity = uni;
        container.classList.add("hidden");
        // Clear course input when university changes
        document.getElementById("mt-name").value = "";
        
        // Auto-select Track to UK because the loaded university list is from the UK dataset
        document.getElementById("mt-track").value = "UK";
      };
      container.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

async function searchCourses(val) {
  const container = document.getElementById("mt-course-results");
  if (!selectedUniversity) {
    alert("Please select a university first");
    document.getElementById("mt-name").value = "";
    return;
  }
  if (!val.trim()) {
    container.classList.add("hidden");
    return;
  }

  try {
    const res = await fetch(`/api/search_courses?uni=${encodeURIComponent(selectedUniversity)}&q=${encodeURIComponent(val)}`);
    const list = await res.json();
    if (list.length === 0) {
      container.classList.add("hidden");
      return;
    }

    container.innerHTML = "";
    container.classList.remove("hidden");
    list.forEach(course => {
      const div = document.createElement("div");
      div.className = "autocomplete-suggestion";
      div.textContent = course.title;
      div.onclick = () => {
        document.getElementById("mt-name").value = course.title;
        container.classList.add("hidden");
        
        // Auto-select corresponding board subjects based on course metadata if available
        if (course.subject_group) {
          console.log("Course subject group CAH code:", course.subject_group);
        }
      };
      container.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

// Hide autocompletes on click outside
document.addEventListener("click", (e) => {
  if (e.target.id !== "mt-uni") {
    document.getElementById("mt-uni-results").classList.add("hidden");
  }
  if (e.target.id !== "mt-name") {
    document.getElementById("mt-course-results").classList.add("hidden");
  }
});
