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

const AP_SUBJECTS = {
  "AP_RESEARCH": "AP Research",
  "AP_SEMINAR": "AP Seminar",
  "AP_ART_HISTORY": "AP Art History",
  "AP_MUSIC_THEORY": "AP Music Theory",
  "AP_STUDIO_ART_2D": "AP Studio Art 2-D Design",
  "AP_STUDIO_ART_3D": "AP Studio Art 3-D Design",
  "AP_STUDIO_ART_DRAWING": "AP Studio Art Drawing",
  "AP_ENGLISH_LANG": "AP English Language & Composition",
  "AP_ENGLISH_LIT": "AP English Literature & Composition",
  "AP_COMPARATIVE_GOV": "AP Comparative Government & Politics",
  "AP_EUROPEAN_HISTORY": "AP European History",
  "AP_HUMAN_GEOGRAPHY": "AP Human Geography",
  "AP_MACROECONOMICS": "AP Macroeconomics",
  "AP_MICROECONOMICS": "AP Microeconomics",
  "AP_PSYCHOLOGY": "AP Psychology",
  "AP_US_GOV": "AP U.S. Government & Politics",
  "AP_US_HISTORY": "AP U.S. History",
  "AP_WORLD_HISTORY": "AP World History: Modern",
  "AP_CALCULUS_AB": "AP Calculus AB",
  "AP_CALCULUS_BC": "AP Calculus BC",
  "AP_COMPUTER_SCIENCE_A": "AP Computer Science A",
  "AP_COMPUTER_SCIENCE_PRINCIPLES": "AP Computer Science Principles",
  "AP_PRECALCULUS": "AP Precalculus",
  "AP_STATISTICS": "AP Statistics",
  "AP_BIOLOGY": "AP Biology",
  "AP_CHEMISTRY": "AP Chemistry",
  "AP_ENVIRONMENTAL_SCIENCE": "AP Environmental Science",
  "AP_PHYSICS_1": "AP Physics 1: Algebra-Based",
  "AP_PHYSICS_2": "AP Physics 2: Algebra-Based",
  "AP_PHYSICS_C_EM": "AP Physics C: Electricity & Magnetism",
  "AP_PHYSICS_C_MECH": "AP Physics C: Mechanics",
  "AP_AFRICAN_AMERICAN_STUDIES": "AP African American Studies",
  "AP_CHINESE_LANG": "AP Chinese Language & Culture",
  "AP_FRENCH_LANG": "AP French Language & Culture",
  "AP_GERMAN_LANG": "AP German Language & Culture",
  "AP_ITALIAN_LANG": "AP Italian Language & Culture",
  "AP_JAPANESE_LANG": "AP Japanese Language & Culture",
  "AP_LATIN": "AP Latin",
  "AP_SPANISH_LANG": "AP Spanish Language & Culture",
  "AP_SPANISH_LIT": "AP Spanish Literature & Culture"
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
  let strongMatch = 0, highRisk = 0, gaps = 0;
  students.forEach(s => {
    const a = cohortAudit[s.id]; if (!a) return;
    let minMatch = 100;
    for (const t in a.targets) {
      const r = a.targets[t];
      const ms = r.match_score !== undefined ? r.match_score : (r.compliant ? 100 : 50);
      minMatch = Math.min(minMatch, ms);
      if (!r.compliant) gaps += r.gaps.length;
    }
    if (minMatch >= 90) strongMatch++;
    else if (minMatch < 70) highRisk++;
  });

  animateNum('m-cohort', students.length);
  animateNum('m-pass', strongMatch);
  animateNum('m-risk', highRisk);
  animateNum('m-gaps', gaps);

  document.getElementById('dash-subtitle').textContent =
    `${students.length} students · ${Object.keys(targets).length} target pathways · real-time audit`;

  renderCohortInsights();
  filterDashboard();
}

function renderCohortInsights() {
  const body = document.getElementById('insights-body');
  if (!body) return;
  body.innerHTML = '';

  // Aggregate gap types
  const gapCounts = {};
  students.forEach(s => {
    const a = cohortAudit[s.id]; if (!a) return;
    for (const t in a.targets) {
      (a.targets[t].gaps || []).forEach(g => {
        const key = g.subject || g.type;
        gapCounts[key] = (gapCounts[key] || 0) + 1;
      });
    }
  });

  const sorted = Object.entries(gapCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);
  if (sorted.length === 0) {
    body.innerHTML = '<span style="color: var(--green);">✔ No common gaps across cohort.</span>';
    return;
  }

  sorted.forEach(([key, count]) => {
    const chip = document.createElement('div');
    chip.style.cssText = 'background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 8px 14px;';
    chip.innerHTML = `<strong style="color:var(--amber);">${count}</strong> <span>students: ${key}</span>`;
    body.appendChild(chip);
  });
}

function getStudentMatchInfo(sid) {
  const a = cohortAudit[sid];
  if (!a) return { minMatch: 100, maxUrg: 0, hasGap: false, names: [], riskLevel: 'Strong Match' };
  let minMatch = 100, maxUrg = 0, hasGap = false;
  const names = [];
  for (const t in a.targets) {
    const r = a.targets[t];
    const ms = r.match_score !== undefined ? r.match_score : (r.compliant ? 100 : 50);
    minMatch = Math.min(minMatch, ms);
    maxUrg = Math.max(maxUrg, r.urgency_score || 0);
    names.push(r.target_name);
    if (!r.compliant) hasGap = true;
  }
  let riskLevel = 'Strong Match';
  if (minMatch < 45) riskLevel = 'Critical';
  else if (minMatch < 70) riskLevel = 'High Risk';
  else if (minMatch < 90) riskLevel = 'Moderate Risk';
  return { minMatch, maxUrg, hasGap, names, riskLevel };
}

function filterDashboard() {
  const searchVal = (document.getElementById('dash-search')?.value || '').toLowerCase();
  const filterVal = document.getElementById('dash-filter')?.value || 'all';
  const sortVal = document.getElementById('dash-sort')?.value || 'name-asc';

  let filtered = students.filter(s => {
    if (searchVal && !s.name.toLowerCase().includes(searchVal)) return false;
    if (filterVal === 'all') return true;
    const info = getStudentMatchInfo(s.id);
    if (filterVal === 'strong') return info.minMatch >= 90;
    if (filterVal === 'moderate') return info.minMatch >= 70 && info.minMatch < 90;
    if (filterVal === 'high') return info.minMatch >= 45 && info.minMatch < 70;
    if (filterVal === 'critical') return info.minMatch < 45;
    return true;
  });

  filtered.sort((a, b) => {
    const infoA = getStudentMatchInfo(a.id);
    const infoB = getStudentMatchInfo(b.id);
    if (sortVal === 'name-asc') return a.name.localeCompare(b.name);
    if (sortVal === 'name-desc') return b.name.localeCompare(a.name);
    if (sortVal === 'match-asc') return infoA.minMatch - infoB.minMatch;
    if (sortVal === 'match-desc') return infoB.minMatch - infoA.minMatch;
    if (sortVal === 'risk-desc') return infoB.maxUrg - infoA.maxUrg;
    return 0;
  });

  renderStudentRows(filtered);
}

function renderStudentRows(list) {
  const rows = document.getElementById('student-rows');
  rows.innerHTML = '';

  if (list.length === 0) {
    rows.innerHTML = '<div class="loading-row">no students match your filters</div>';
    return;
  }

  list.forEach(s => {
    const info = getStudentMatchInfo(s.id);
    const { minMatch, maxUrg, hasGap, names, riskLevel } = info;

    const filled = Math.round((Math.min(minMatch, 100) / 100) * 8);
    const empty = 8 - filled;
    let riskColor, markerClass, statusText, statusClass;
    if (minMatch >= 90) {
      riskColor = 'var(--green)'; markerClass = 'nm-pass'; statusText = riskLevel; statusClass = 'st-pass';
    } else if (minMatch >= 70) {
      riskColor = 'var(--amber)'; markerClass = 'nm-warn'; statusText = riskLevel; statusClass = 'st-warn';
    } else {
      riskColor = 'var(--red)'; markerClass = 'nm-crit'; statusText = riskLevel; statusClass = 'st-crit';
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
        <div class="risk-pct" style="color:${riskColor}">${minMatch}%</div>
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

function updateManageSubjectGradesUI() {
  const container = document.getElementById('mf-subject-grades-container');
  const section = document.getElementById('mf-subject-grades-section');
  if (!container || !section) return;

  const checkedCbs = document.querySelectorAll('#mf-subjects input:checked');
  const checkedSubjects = [...checkedCbs].map(cb => cb.value);

  if (checkedSubjects.length === 0) {
    section.style.display = 'none';
    container.innerHTML = '';
    return;
  }

  const existingValues = {};
  container.querySelectorAll('input').forEach(input => {
    existingValues[input.dataset.subject] = input.value;
  });

  section.style.display = 'block';
  container.innerHTML = '';

  checkedSubjects.forEach(sub => {
    const field = document.createElement('div');
    field.className = 'field';
    field.style.marginBottom = '8px';
    const val = existingValues[sub] !== undefined ? existingValues[sub] : '';
    field.innerHTML = `
      <label style="font-size: 0.72rem; color: var(--text-2); margin-bottom: 4px; display: block;">${sub}</label>
      <input type="number" class="mf-subj-mark" data-subject="${sub}" min="0" max="100" placeholder="e.g. 95" value="${val}" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
    `;
    container.appendChild(field);
  });
}

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
    cb.addEventListener('change', () => {
      lbl.classList.toggle('checked', cb.checked);
      updateManageSubjectGradesUI();
    });
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

  // Reset/update subject grades UI when board/subjects change
  updateManageSubjectGradesUI();
}

let manageSelectedAPs = {};

function addManageAPRow(key, score) {
  const container = document.getElementById('mf-ap-list');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.style.gridTemplateColumns = '2fr 1fr auto';
  row.style.marginBottom = '4px';
  row.style.alignItems = 'center';
  
  row.innerHTML = `
    <span style="font-family:var(--sans); font-size:0.8rem; color:var(--text-1);">${AP_SUBJECTS[key] || key}</span>
    <span style="font-family:var(--mono); font-size:0.8rem; color:var(--accent); font-weight:600;">Score: ${score}</span>
    <button type="button" class="btn-delete-sm" onclick="removeManageAP('${key}')">✕</button>
  `;
  container.appendChild(row);
}

function renderManageAPs() {
  const container = document.getElementById('mf-ap-list');
  container.innerHTML = '';
  for (const key in manageSelectedAPs) {
    addManageAPRow(key, manageSelectedAPs[key]);
  }
}

function addManageAPFromSelect() {
  const subEl = document.getElementById('mf-ap-subject');
  const scoreEl = document.getElementById('mf-ap-score');
  const key = subEl.value;
  const score = parseInt(scoreEl.value);

  if (!key) {
    alert("Please select an AP subject first");
    return;
  }

  manageSelectedAPs[key] = score;
  renderManageAPs();

  // Reset select
  subEl.value = "";
}

function removeManageAP(key) {
  delete manageSelectedAPs[key];
  renderManageAPs();
}

window.addManageAPFromSelect = addManageAPFromSelect;
window.removeManageAP = removeManageAP;

const DEFAULT_MANAGE_G10_SUBJECTS = ["Mathematics", "Science", "Social Science", "English", "Hindi / Second Language"];

function initManageG10Subjects() {
  const container = document.getElementById('mf-g10-subject-grades-container');
  if (!container) return;
  if (container.children.length > 0) return;

  DEFAULT_MANAGE_G10_SUBJECTS.forEach(sub => {
    addManageG10SubjectRow(sub);
  });
}

function addManageG10SubjectRow(subjectName = '') {
  const inputEl = document.getElementById('mf-g10-custom-subj');
  const sub = subjectName || (inputEl ? inputEl.value.trim() : '');
  if (!sub) return;

  const container = document.getElementById('mf-g10-subject-grades-container');
  if (!container) return;

  if (container.querySelector(`[data-g10-subject="${sub}"]`)) {
    if (inputEl) inputEl.value = '';
    return;
  }

  const field = document.createElement('div');
  field.className = 'field';
  field.style.marginBottom = '8px';
  field.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <label style="font-size: 0.72rem; color: var(--text-2); display: block;">${sub}</label>
      <button type="button" class="btn-delete-sm" onclick="this.closest('.field').remove()" style="font-size:0.65rem; padding: 0 4px;">✕</button>
    </div>
    <input type="number" class="mf-g10-subj-mark" data-g10-subject="${sub}" min="0" max="100" placeholder="e.g. 90" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
  `;
  container.appendChild(field);
  if (inputEl && !subjectName) inputEl.value = '';
}

function addManageCustomBoardSubject() {
  const input = document.getElementById('mf-custom-subject-input');
  if (!input) return;
  const sub = input.value.trim();
  if (!sub) return;

  const subEl = document.getElementById('mf-subjects');
  if (!subEl) return;

  const lbl = document.createElement('label');
  lbl.className = 'sc-label checked';
  lbl.innerHTML = `<input type="checkbox" value="${sub}" checked />${sub}`;
  const cb = lbl.querySelector('input');
  cb.addEventListener('change', () => {
    lbl.classList.toggle('checked', cb.checked);
    updateManageSubjectGradesUI();
  });
  subEl.appendChild(lbl);

  input.value = '';
  updateManageSubjectGradesUI();
}

function initManageForm() {
  updateManageSubjectsGrid();
  initManageG10Subjects();

  // Populate AP subject select
  const apSelect = document.getElementById('mf-ap-subject');
  if (apSelect) {
    apSelect.innerHTML = '<option value="" disabled selected>Select AP Subject...</option>';
    for (const key in AP_SUBJECTS) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = AP_SUBJECTS[key];
      apSelect.appendChild(opt);
    }
  }

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

function addPortfolioRow(activity = '', desc = '') {
  const list = document.getElementById('mf-portfolio-list');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.innerHTML = `
    <input type="text" placeholder="activity name" class="pf-activity" value="${activity}" />
    <input type="text" placeholder="description" class="pf-desc" value="${desc}" />
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

  const g10SubjectsGrades = {};
  document.querySelectorAll('.mf-g10-subj-mark').forEach(input => {
    const mark = parseInt(input.value);
    if (!isNaN(mark)) {
      g10SubjectsGrades[input.dataset.g10Subject] = mark;
    }
  });
  grades.class_10_subjects = g10SubjectsGrades;

  const subjectsGrades = {};
  document.querySelectorAll('.mf-subj-mark').forEach(input => {
    const mark = parseInt(input.value);
    if (!isNaN(mark)) {
      subjectsGrades[input.dataset.subject] = mark;
    }
  });
  grades.subjects = subjectsGrades;

  const tests = {};
  const sat = document.getElementById('mf-sat').value;
  if (sat) tests.SAT = parseInt(sat);
  for (const apKey in manageSelectedAPs) {
    tests[apKey] = manageSelectedAPs[apKey];
  }

  const portfolio = [];
  document.querySelectorAll('#mf-portfolio-list .portfolio-row').forEach(row => {
    const act = row.querySelector('.pf-activity').value.trim();
    const d = row.querySelector('.pf-desc').value.trim();
    if (act) portfolio.push({ activity: act, description: d });
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

  // Dynamically build subject grade inputs
  updateManageSubjectGradesUI();

  // Populate actual subject grades
  const subjectsGrades = s.grades?.subjects || {};
  document.querySelectorAll('.mf-subj-mark').forEach(input => {
    const sub = input.dataset.subject;
    if (subjectsGrades[sub] !== undefined) {
      input.value = subjectsGrades[sub];
    }
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

  // Populate Grade 10 subject marks
  const g10Container = document.getElementById('mf-g10-subject-grades-container');
  if (g10Container) {
    g10Container.innerHTML = '';
    const g10Subjs = s.grades?.class_10_subjects || {};
    const keys = Object.keys(g10Subjs).length > 0 ? Object.keys(g10Subjs) : DEFAULT_MANAGE_G10_SUBJECTS;
    keys.forEach(sub => {
      addManageG10SubjectRow(sub);
    });
    document.querySelectorAll('.mf-g10-subj-mark').forEach(input => {
      const sub = input.dataset.g10Subject;
      if (g10Subjs[sub] !== undefined) {
        input.value = g10Subjs[sub];
      }
    });
  }

  // Populate APs
  manageSelectedAPs = {};
  for (const apKey in AP_SUBJECTS) {
    if (s.standardized_tests && s.standardized_tests[apKey] !== undefined) {
      manageSelectedAPs[apKey] = s.standardized_tests[apKey];
    }
  }
  renderManageAPs();

  // Portfolio
  document.getElementById('mf-portfolio-list').innerHTML = '';
  (s.portfolio || []).forEach(p => addPortfolioRow(p.activity, p.description));

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

  const g10Container = document.getElementById('mf-g10-subject-grades-container');
  if (g10Container) {
    g10Container.innerHTML = '';
    initManageG10Subjects();
  }

  // Reset APs
  manageSelectedAPs = {};
  renderManageAPs();

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
    const ms = t.match_score !== undefined ? t.match_score : (t.compliant ? 100 : 50);
    const rl = t.risk_level || (ms >= 90 ? 'Strong Match' : ms >= 70 ? 'Moderate Risk' : ms >= 45 ? 'High Risk' : 'Critical');
    const badgeColor = ms >= 90 ? 'tb-pass' : ms >= 70 ? 'tb-warn' : 'tb-fail';

    // Gaps
    const gb = document.createElement('div'); gb.className = 'target-block';
    gb.innerHTML = `<div class="tb-header"><span class="tb-name">${t.target_name}</span><span class="tb-badge ${badgeColor}">${ms}% Match · ${rl}</span></div>`;
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

    // Data freshness warning in drawer
    const verified = (t.gaps && t.gaps.length > 0 && t.gaps[0].last_verified) ? t.gaps[0].last_verified : null;
    if (verified) {
      const freshness = document.createElement('div');
      freshness.style.cssText = 'font-size: 0.7rem; color: var(--text-3); margin-top: 10px; font-style: italic;';
      freshness.textContent = `⚠️ Requirements data last verified: ${verified}`;
      gbody.appendChild(freshness);
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
  const subjects = currentStudent ? (BOARD_SUBJECTS[currentStudent.board] || BOARD_SUBJECTS["CBSE"]) : BOARD_SUBJECTS["CBSE"];
  subjects.forEach(sub => {
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

async function runCounselorAgentCommand() {
  const input = document.getElementById('cc-command-input');
  if (!input) return;
  const command = input.value.trim();
  if (!command) return;

  const responseContainer = document.getElementById('cc-agent-response');
  if (!responseContainer) return;

  responseContainer.style.display = 'block';
  responseContainer.style.borderColor = 'var(--border)';
  responseContainer.innerHTML = '<span style="color:var(--text-3); font-style:italic;">Agent is executing command...</span>';
  input.value = '';

  try {
    const res = await fetch('/api/counselor_agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
    const data = await res.json();

    // Render markdown to HTML
    let html = data.response
      .replace(/\#\#\# (.*?)\n/g, '<h4 style="margin: 8px 0 4px; color: var(--amber); font-family: var(--sans);">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\- (.*?)\n/g, '<li style="margin-left: 12px; margin-bottom: 4px; font-family: var(--sans);">$1</li>')
      .replace(/\n/g, '<br>');

    responseContainer.innerHTML = html;
  } catch (err) {
    responseContainer.innerHTML = '<span style="color:var(--red);">Failed to execute agent command.</span>';
  }
}

window.runCounselorAgentCommand = runCounselorAgentCommand;
