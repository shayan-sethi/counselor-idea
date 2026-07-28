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
    const g10BoardSelect = document.getElementById('mf-g10-board');
    if (g10BoardSelect) {
      g10BoardSelect.addEventListener('change', updateManageG10Placeholders);
    }
  } catch (e) {
    document.getElementById('student-rows').innerHTML =
      '<div class="loading-row" style="color:var(--red)">✕ failed to connect to engine</div>';
  }
}

function getPlaceholderForBoard(board) {
  if (board === 'IB' || board === 'IB MYP') return "e.g. 7";
  if (board === 'IGCSE' || board === 'A-Levels') return "e.g. A*";
  return "e.g. 95";
}

function updateManageG10Placeholders() {
  const g10Board = document.getElementById('mf-g10-board')?.value;
  const ph = getPlaceholderForBoard(g10Board);
  document.querySelectorAll('.mf-g10-subj-mark').forEach(input => {
    input.placeholder = ph;
  });
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
  ['dashboard', 'manage', 'predictor', 'reports', 'radar', 'shortlist', 'calendar'].forEach(id => {
    const el = document.getElementById(`view-${id}`);
    if (el) el.classList.toggle('hidden', id !== v);
    const tabMap = { 
      'dashboard': 'dash', 'manage': 'manage', 'predictor': 'pred', 
      'reports': 'reports', 'radar': 'radar', 'shortlist': 'shortlist', 'calendar': 'calendar' 
    };
    const tabEl = document.getElementById(`tab-${tabMap[id]}`);
    if (tabEl) tabEl.classList.toggle('active', id === v);
  });
  if (v === 'manage') renderManageList();
  if (v === 'reports') renderReportsView();
  if (v === 'radar') renderRadarView();
  if (v === 'shortlist') renderShortlistView();
  if (v === 'calendar') renderCalendarView();
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
    const board = document.getElementById('mf-board').value;
    const ph = getPlaceholderForBoard(board);
    field.innerHTML = `
      <label style="font-size: 0.72rem; color: var(--text-2); margin-bottom: 4px; display: block;">${sub}</label>
      <input type="text" class="mf-subj-mark" data-subject="${sub}" placeholder="${ph}" value="${val}" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
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
  const g10Board = document.getElementById('mf-g10-board')?.value;
  const ph = getPlaceholderForBoard(g10Board);
  field.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <label style="font-size: 0.72rem; color: var(--text-2); display: block;">${sub}</label>
      <button type="button" class="btn-delete-sm" onclick="this.closest('.field').remove()" style="font-size:0.65rem; padding: 0 4px;">✕</button>
    </div>
    <input type="text" class="mf-g10-subj-mark" data-g10-subject="${sub}" placeholder="${ph}" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
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
  const g10Board = document.getElementById('mf-g10-board')?.value;
  if (g10Board) grades.g10_board = g10Board;
  const g10 = document.getElementById('mf-g10').value.trim();
  const g11 = document.getElementById('mf-g11').value.trim();
  const gexp = document.getElementById('mf-gexp').value.trim();
  if (g10) grades.class_10_aggregate = g10;
  if (g11) grades.class_11_aggregate = g11;
  if (gexp) grades.current_expected_board = gexp;

  const g10SubjectsGrades = {};
  document.querySelectorAll('.mf-g10-subj-mark').forEach(input => {
    const mark = input.value.trim();
    if (mark) {
      g10SubjectsGrades[input.dataset.g10Subject] = mark;
    }
  });
  grades.class_10_subjects = g10SubjectsGrades;

  const subjectsGrades = {};
  document.querySelectorAll('.mf-subj-mark').forEach(input => {
    const mark = input.value.trim();
    if (mark) {
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
  if (s.grades?.g10_board) document.getElementById('mf-g10-board').value = s.grades.g10_board;
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

  container.innerHTML = '<div style="padding:10px;text-align:center;color:var(--text-3); font-size: 0.8rem;">⏳ Searching universities...</div>';
  container.classList.remove("hidden");

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

/* ═══════════════════════════════════════════════════
   COUNSELOR MODAL AUTOMATED INGESTION
   ═══════════════════════════════════════════════════ */

async function ingestCounselorDocument() {
  const fileInput = document.getElementById('counselor-ingest-file');
  const files = fileInput ? fileInput.files : [];
  const statusEl = document.getElementById('counselor-ingest-status');

  if (!files || files.length === 0) {
    alert('Please select at least one document to ingest.');
    return;
  }

  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.style.color = 'var(--amber)';
    statusEl.innerHTML = 'Parsing files... Auto-populating student form via PRISM AI.';
  }

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  formData.append('auto_save', 'false');

  try {
    const res = await fetch('/api/ingest_documents', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to ingest document.');

    const s = data.student;

    if (s.name) document.getElementById('mf-name').value = s.name;
    if (s.board) document.getElementById('mf-board').value = s.board;
    if (s.class_level) document.getElementById('mf-class').value = s.class_level;
    if (s.grades && s.grades.current_expected_board) {
      document.getElementById('mf-gexp').value = s.grades.current_expected_board;
    }
    if (s.standardized_tests && s.standardized_tests.SAT) {
      document.getElementById('mf-sat').value = s.standardized_tests.SAT;
    }
    if (s.cuet_subjects && s.cuet_subjects.length > 0) {
      document.getElementById('mf-cuet').value = s.cuet_subjects.join(', ');
    }

    const g10Subs = s.grades ? (s.grades.g10_subjects || s.grades.grade_10_subjects || s.grades.subjects) : null;
    if (g10Subs) {
      for (const [subName, subMark] of Object.entries(g10Subs)) {
        if (typeof addManageG10SubjectRow === 'function') addManageG10SubjectRow(subName);
        const subInput = document.querySelector(`.mf-g10-subj-mark[data-g10-subject="${subName}"]`);
        if (subInput && subMark) {
          subInput.value = typeof subMark === 'number' ? subMark : parseFloat(subMark) || 95;
        }
      }
    }

    if (statusEl) {
      statusEl.style.color = 'var(--green)';
      statusEl.innerHTML = `Auto-filled details for <strong>${s.name || 'Student'}</strong>. Review fields and click "add student".`;
    }
  } catch (err) {
    if (statusEl) {
      statusEl.style.color = 'var(--red)';
      statusEl.innerHTML = `Ingestion error: ${err.message}`;
    }
  }
}
window.ingestCounselorDocument = ingestCounselorDocument;

// ══════════════════════════════════════════════
//  REPORTS
// ══════════════════════════════════════════════

let currentReportSubView = 'student';

function switchReportSubView(type) {
  currentReportSubView = type;
  document.getElementById('report-sec-student').classList.toggle('hidden', type !== 'student');
  document.getElementById('report-sec-cohort').classList.toggle('hidden', type !== 'cohort');
  
  const btnStud = document.getElementById('btn-report-sub-student');
  const btnCoho = document.getElementById('btn-report-sub-cohort');
  
  if (type === 'student') {
    btnStud.style.color = 'var(--accent)';
    btnStud.style.borderColor = 'var(--accent)';
    btnCoho.style.color = 'var(--text-3)';
    btnCoho.style.borderColor = 'var(--border)';
    renderStudentReportSelector();
  } else {
    btnCoho.style.color = 'var(--accent)';
    btnCoho.style.borderColor = 'var(--accent)';
    btnStud.style.color = 'var(--text-3)';
    btnStud.style.borderColor = 'var(--border)';
    renderCohortReport();
  }
}
window.switchReportSubView = switchReportSubView;

function renderReportsView() {
  switchReportSubView(currentReportSubView);
}
window.renderReportsView = renderReportsView;

function renderStudentReportSelector() {
  const sel = document.getElementById('report-student-select');
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '';
  students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.name} (${s.id})`;
    sel.appendChild(opt);
  });
  if (currentVal && students.some(s => s.id === currentVal)) {
    sel.value = currentVal;
  } else if (students.length > 0) {
    sel.value = students[0].id;
  }
  if (sel.value) {
    onReportStudentChange(sel.value);
  }
}

async function onReportStudentChange(studentId) {
  const s = students.find(x => x.id === studentId);
  if (!s) return;
  
  // Set metadata
  document.getElementById('rep-date').textContent = new Date().toLocaleDateString();
  document.getElementById('rep-name').textContent = s.name;
  document.getElementById('rep-id').textContent = s.id;
  document.getElementById('rep-board').textContent = `${s.board} · Class ${s.class_level}`;
  document.getElementById('rep-grade').textContent = s.grades && s.grades.current_expected_board ? s.grades.current_expected_board : '—';
  
  // Set inputs
  document.getElementById('report-notes-input').value = s.counselor_notes || '';
  document.getElementById('rep-counselor-notes-text').textContent = s.counselor_notes || 'No custom counselor remarks appended. Use the notes panel above to update.';
  
  // Build subjects list
  document.getElementById('rep-subjects-list').textContent = s.board_subjects ? s.board_subjects.join(', ') : '—';
  const cuetWrap = document.getElementById('rep-cuet-subjects-wrap');
  if (s.cuet_subjects && s.cuet_subjects.length > 0) {
    cuetWrap.classList.remove('hidden');
    document.getElementById('rep-cuet-list').textContent = s.cuet_subjects.join(', ');
  } else {
    cuetWrap.classList.add('hidden');
  }
  
  // Portfolio tier
  let pTier = 3;
  if (s.portfolio && s.portfolio.length > 0) {
    pTier = Math.min(...s.portfolio.map(p => p.tier || 3));
  }
  document.getElementById('rep-portfolio-tier').innerHTML = `Tier ${pTier} (${s.portfolio && s.portfolio.length ? s.portfolio.length : 0} activities)`;

  // Fetch compliance & gaps from cohortAudit
  const audit = cohortAudit[s.id];
  const listCont = document.getElementById('rep-targets-list');
  listCont.innerHTML = '';
  
  let overallCompliant = true;
  let minMatchScore = 100;
  
  // Dynamic Checklist variables
  let boardSubjectsOk = true;
  let gradesOk = true;
  let timelinesOk = true;
  let portfolioOk = true;
  let cuetOk = true;
  
  let boardSubjectsMsg = "All compulsory subjects registered";
  let gradesMsg = "Expected grades meet cutoffs";
  let timelinesMsg = "No upcoming deadline conflicts";
  let portfolioMsg = "Portfolio strength matches target level";
  let cuetMsg = "CUET subject mapping is valid";
  
  if (audit && Object.keys(audit.targets).length > 0) {
    for (const tid in audit.targets) {
      const t = audit.targets[tid];
      const matchScore = t.match_score !== undefined ? t.match_score : (t.compliant ? 100 : 50);
      if (!t.compliant) overallCompliant = false;
      minMatchScore = Math.min(minMatchScore, matchScore);
      
      const card = document.createElement('div');
      card.style.border = '1px solid var(--border)';
      card.style.padding = '14px';
      card.style.background = 'var(--surface)';
      card.style.marginBottom = '12px';
      
      let statusHtml = t.compliant 
        ? `<span style="color: var(--green); font-weight:700;">✓ ELIGIBLE</span>`
        : `<span style="color: var(--red); font-weight:700;">✕ INELIGIBLE (${t.gaps.length} gaps)</span>`;
      
      let gapsHtml = '';
      if (t.gaps && t.gaps.length > 0) {
        gapsHtml = `<div style="margin-top: 8px;">`;
        t.gaps.forEach(g => {
          gapsHtml += `
            <div style="font-size: 0.72rem; color: var(--red); padding: 6px 10px; border-left: 3px solid var(--red); background: rgba(255,64,64,0.03); margin-bottom: 6px;">
              <strong>${g.subject || 'Rule'}:</strong> ${g.description}
            </div>`;
            
          // Categorize gaps for checklist
          if (g.type === 'subject_missing') {
            boardSubjectsOk = false;
            boardSubjectsMsg = g.description;
          } else if (g.type === 'grade_cutoff_violation') {
            gradesOk = false;
            gradesMsg = g.description;
          } else if (g.type === 'timeline_deadline' || g.type === 'test_missing' || g.type === 'test_score_low') {
            timelinesOk = false;
            timelinesMsg = g.description;
          } else if (g.type === 'portfolio_tier_low') {
            portfolioOk = false;
            portfolioMsg = g.description;
          } else if (g.type === 'cuet_unlawful_domain' || g.type === 'cuet_missing_subject') {
            cuetOk = false;
            cuetMsg = g.description;
          }
        });
        gapsHtml += `</div>`;
      }
      
      let remHtml = '';
      if (t.remediations && t.remediations.length > 0) {
        remHtml = `<div style="margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 8px;">
          <div style="font-family: var(--mono); font-size: 0.62rem; color: var(--accent); margin-bottom: 6px; font-weight: 700; letter-spacing: 0.04em;">⚡ PRISMA REMEDIATION ADVICE:</div>`;
        t.remediations.forEach(r => {
          const feasColor = r.feasibility === 'HIGH' ? 'var(--green)' : r.feasibility === 'MEDIUM' ? 'var(--amber)' : 'var(--red)';
          remHtml += `
            <div style="font-size: 0.72rem; color: var(--text-2); margin-bottom: 8px; padding: 8px; border: 1px solid var(--border); background: rgba(255,255,255,0.01);">
              <div style="font-weight: 600; color: var(--text-1); line-height: 1.4;">${r.remediation}</div>
              <div style="margin-top: 4px; font-size: 0.68rem; color: var(--text-3); display: flex; justify-content: space-between;">
                <span><strong>Task:</strong> ${r.action_item}</span>
                <span style="font-family: var(--mono); color: ${feasColor}; font-weight: 700;">[FEASIBILITY: ${r.feasibility}]</span>
              </div>
            </div>`;
        });
        remHtml += `</div>`;
      }
      
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="font-size: 0.85rem; color: var(--text-1);">${t.target_name}</strong>
          <span style="font-family: var(--mono); font-size: 0.75rem; font-weight:700; color:${matchScore >= 90 ? 'var(--green)' : matchScore >= 70 ? 'var(--amber)' : 'var(--red)'};">${matchScore}% match</span>
        </div>
        <div style="font-size: 0.72rem; color: var(--text-2); display: flex; justify-content: space-between;">
          <span>Track: ${t.track}</span>
          <span>${statusHtml}</span>
        </div>
        ${gapsHtml}
        ${remHtml}
      `;
      listCont.appendChild(card);
    }
  } else {
    listCont.innerHTML = `<div style="color:var(--text-3); font-size:0.8rem; font-style:italic;">No target pathways added to this student profile yet.</div>`;
  }
  
  // Render Dynamic Checklist HTML
  const checklistCont = document.getElementById('rep-readiness-checklist');
  if (checklistCont) {
    let showCuet = s.track === 'India' || (audit && Object.values(audit.targets).some(t => t.track === 'India'));
    checklistCont.innerHTML = `
      <div style="border: 1px solid var(--border); padding: 16px; background: var(--surface); margin-bottom: 24px;">
        <div style="font-family: var(--mono); font-size: 0.72rem; color: var(--text-3); text-transform: uppercase; margin-bottom: 12px; font-weight: 700; letter-spacing: 0.05em;">📌 PATHWAY READINESS CHECKLIST</div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px 20px;">
          <!-- Board Subjects -->
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <span style="color: ${boardSubjectsOk ? 'var(--green)' : 'var(--red)'}; font-weight: bold; font-size: 1.1rem; line-height: 1;">${boardSubjectsOk ? '✓' : '✕'}</span>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-1);">Board Subject Registration</div>
              <div style="font-size: 0.68rem; color: var(--text-3); margin-top: 2px; line-height: 1.3;">${boardSubjectsMsg}</div>
            </div>
          </div>
          <!-- Academic Cutoffs -->
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <span style="color: ${gradesOk ? 'var(--green)' : 'var(--amber)'}; font-weight: bold; font-size: 1.1rem; line-height: 1;">${gradesOk ? '✓' : '✕'}</span>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-1);">Academic Performance Cutoffs</div>
              <div style="font-size: 0.68rem; color: var(--text-3); margin-top: 2px; line-height: 1.3;">${gradesMsg}</div>
            </div>
          </div>
          <!-- Timelines & Exams -->
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <span style="color: ${timelinesOk ? 'var(--green)' : 'var(--amber)'}; font-weight: bold; font-size: 1.1rem; line-height: 1;">${timelinesOk ? '✓' : '✕'}</span>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-1);">Standardized Tests & Deadlines</div>
              <div style="font-size: 0.68rem; color: var(--text-3); margin-top: 2px; line-height: 1.3;">${timelinesMsg}</div>
            </div>
          </div>
          <!-- Portfolio check -->
          <div style="display: flex; gap: 10px; align-items: flex-start;">
            <span style="color: ${portfolioOk ? 'var(--green)' : 'var(--amber)'}; font-weight: bold; font-size: 1.1rem; line-height: 1;">${portfolioOk ? '✓' : '✕'}</span>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-1);">Extracurricular Portfolio Tier</div>
              <div style="font-size: 0.68rem; color: var(--text-3); margin-top: 2px; line-height: 1.3;">${portfolioMsg}</div>
            </div>
          </div>
          <!-- CUET Mapping (if applicable) -->
          ${showCuet ? `
          <div style="display: flex; gap: 10px; align-items: flex-start; grid-column: span 2;">
            <span style="color: ${cuetOk ? 'var(--green)' : 'var(--red)'}; font-weight: bold; font-size: 1.1rem; line-height: 1;">${cuetOk ? '✓' : '✕'}</span>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-1);">CUET Subject Alignment</div>
              <div style="font-size: 0.68rem; color: var(--text-3); margin-top: 2px; line-height: 1.3;">${cuetMsg}</div>
            </div>
          </div>` : ''}
        </div>
      </div>`;
  }
  
  // Set overall status
  const statEl = document.getElementById('rep-status');
  if (overallCompliant && audit && Object.keys(audit.targets).length > 0) {
    statEl.textContent = 'ON TRACK';
    statEl.style.color = 'var(--green)';
  } else if (minMatchScore >= 70 && audit && Object.keys(audit.targets).length > 0) {
    statEl.textContent = 'NEEDS ATTENTION';
    statEl.style.color = 'var(--amber)';
  } else if (audit && Object.keys(audit.targets).length > 0) {
    statEl.textContent = 'CRITICAL RISK';
    statEl.style.color = 'var(--red)';
  } else {
    statEl.textContent = 'NO TARGETS';
    statEl.style.color = 'var(--text-3)';
  }

  // Load ML predictions dynamically based on the student's top target course
  let topTarget = null;
  if (audit && Object.keys(audit.targets).length > 0) {
    // Find the first target
    const tid = Object.keys(audit.targets)[0];
    topTarget = audit.targets[tid];
  }
  
  let targetSubjectCode = "CAH17"; // Default Computing
  let aim = "BSc";
  if (topTarget) {
    const tName = topTarget.target_name.toLowerCase();
    if (tName.includes("eco") || tName.includes("business")) {
      targetSubjectCode = "CAH25";
      aim = "BSc";
    } else if (tName.includes("math")) {
      targetSubjectCode = "CAH11";
      aim = "BSc";
    }
  }
  
  // Convert board aggregate expectation to UCAS tariff roughly
  let expectedPct = 85.0;
  if (s.grades && s.grades.current_expected_board) {
    expectedPct = parseFloat(s.grades.current_expected_board) || 85.0;
  }
  let estimatedTariff = 120.0;
  if (expectedPct >= 95) estimatedTariff = 156.0;
  else if (expectedPct >= 90) estimatedTariff = 144.0;
  else if (expectedPct >= 85) estimatedTariff = 128.0;
  else if (expectedPct >= 80) estimatedTariff = 112.0;

  try {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subject: targetSubjectCode,
        aim: aim,
        country: 'England',
        tariff: estimatedTariff,
        nss: 84.5,
        tef: 'Gold',
        tef_exp: 'Gold',
        tef_out: 'Gold',
        foundation: 0,
        honours: 1,
        sandwich: 0,
        yearabroad: 0
      })
    });
    const d = await res.json();
    const p = d.predictions;
    if (p) {
      document.getElementById('rep-ml-salary').textContent = p.salary != null ? `£${Math.round(p.salary).toLocaleString('en-GB')}` : '—';
      document.getElementById('rep-ml-employment').textContent = p.employment != null ? `${p.employment.toFixed(1)}%` : '—';
      document.getElementById('rep-ml-continuation').textContent = p.continuation != null ? `${p.continuation.toFixed(1)}%` : '—';
      
      document.getElementById('rep-ml-salary-bar').style.width = p.salary != null ? `${Math.min(100, (p.salary / 50000) * 100)}%` : '0%';
      document.getElementById('rep-ml-employment-bar').style.width = p.employment != null ? `${p.employment}%` : '0%';
      document.getElementById('rep-ml-continuation-bar').style.width = p.continuation != null ? `${p.continuation}%` : '0%';
    }
  } catch (err) {
    console.error("Failed to run predictions for report:", err);
  }
}
window.onReportStudentChange = onReportStudentChange;

async function saveReportNotes() {
  const sel = document.getElementById('report-student-select');
  if (!sel || !sel.value) return;
  const notesVal = document.getElementById('report-notes-input').value;
  
  const studentId = sel.value;
  const s = students.find(x => x.id === studentId);
  if (!s) return;
  
  const btn = document.getElementById('btn-save-report-notes');
  btn.disabled = true;
  btn.textContent = 'saving…';
  
  try {
    const res = await fetch(`/api/students/${studentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...s, counselor_notes: notesVal })
    });
    if (res.ok) {
      alert("Notes saved successfully!");
      s.counselor_notes = notesVal;
      document.getElementById('rep-counselor-notes-text').textContent = notesVal || 'No custom counselor remarks appended. Use the notes panel above to update.';
    } else {
      alert("Failed to save notes.");
    }
  } catch (err) {
    console.error(err);
    alert("Error saving notes: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'save notes to profile';
  }
}
window.saveReportNotes = saveReportNotes;

function renderCohortReport() {
  document.querySelectorAll('.cohort-rep-date').forEach(el => {
    el.textContent = new Date().toLocaleDateString();
  });
  
  document.getElementById('rep-cohort-size').textContent = students.length;
  document.getElementById('rep-cohort-total').textContent = students.length;
  
  let strongCount = 0;
  let riskCount = 0;
  let criticalCount = 0;
  
  const tableBody = document.getElementById('cohort-report-table-body');
  tableBody.innerHTML = '';
  
  const commonGaps = {};
  
  students.forEach(s => {
    const audit = cohortAudit[s.id];
    let minMatch = 100;
    let targetNames = [];
    
    if (audit && Object.keys(audit.targets).length > 0) {
      for (const tid in audit.targets) {
        const t = audit.targets[tid];
        targetNames.push(t.target_name);
        const matchScore = t.match_score !== undefined ? t.match_score : (t.compliant ? 100 : 50);
        minMatch = Math.min(minMatch, matchScore);
        
        t.gaps.forEach(g => {
          const sub = g.subject || 'General';
          commonGaps[sub] = (commonGaps[sub] || 0) + 1;
        });
      }
    }
    
    if (minMatch >= 90) strongCount++;
    else if (minMatch >= 70) riskCount++;
    else criticalCount++;
    
    let statusText = 'CRITICAL';
    let statusColor = 'var(--red)';
    if (minMatch >= 90) {
      statusText = 'STRONG';
      statusColor = 'var(--green)';
    } else if (minMatch >= 70) {
      statusText = 'MODERATE';
      statusColor = 'var(--amber)';
    } else if (targetNames.length === 0) {
      statusText = 'NO TARGETS';
      statusColor = 'var(--text-3)';
      minMatch = '—';
    }
    
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid var(--border)';
    tr.style.height = '36px';
    tr.innerHTML = `
      <td style="font-family: var(--mono);">${s.id}</td>
      <td style="font-weight: 700; color: var(--text-1);">${s.name}</td>
      <td>${s.board} (Cl. ${s.class_level})</td>
      <td style="color: var(--text-2);">${targetNames.length > 0 ? targetNames.join('; ') : 'None'}</td>
      <td style="text-align: right; font-family: var(--mono); font-weight:700;">${minMatch}${typeof minMatch === 'number' ? '%' : ''}</td>
      <td style="text-align: right; font-weight:700; color:${statusColor};">${statusText}</td>
    `;
    tableBody.appendChild(tr);
  });
  
  document.getElementById('rep-cohort-strong').textContent = strongCount;
  document.getElementById('rep-cohort-risk').textContent = riskCount;
  document.getElementById('rep-cohort-critical').textContent = criticalCount;
  
  // Gap frequencies
  const gapContainer = document.getElementById('cohort-report-gaps-summary');
  gapContainer.innerHTML = '';
  const sortedGaps = Object.entries(commonGaps).sort((a,b) => b[1] - a[1]);
  if (sortedGaps.length > 0) {
    sortedGaps.forEach(([sub, freq]) => {
      const el = document.createElement('div');
      el.style.border = '1px solid var(--border)';
      el.style.background = 'var(--surface)';
      el.style.padding = '12px';
      el.innerHTML = `
        <div style="font-family: var(--mono); font-size: 0.62rem; color: var(--text-3); text-transform: uppercase;">SUBJECT: ${sub}</div>
        <div style="font-size: 1.2rem; font-weight: 800; color: var(--red); margin-top: 4px;">${freq} Students Affected</div>
      `;
      gapContainer.appendChild(el);
    });
  } else {
    gapContainer.innerHTML = `<div style="color:var(--text-3); font-size:0.8rem; font-style:italic;">No active prerequisite gaps detected across the cohort.</div>`;
  }
}
window.renderCohortReport = renderCohortReport;

function printReport() {
  window.print();
}
window.printReport = printReport;

function printCohortReport() {
  window.print();
}
window.printCohortReport = printCohortReport;

// ══════════════════════════════════════════════
//  OPPORTUNITY RADAR
// ══════════════════════════════════════════════

function renderRadarView() {
  const sel = document.getElementById('radar-student-select');
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '';
  students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.name} (${s.id})`;
    sel.appendChild(opt);
  });
  if (currentVal && students.some(s => s.id === currentVal)) {
    sel.value = currentVal;
  } else if (students.length > 0) {
    sel.value = students[0].id;
  }
  if (sel.value) {
    onRadarStudentChange(sel.value);
  }
}
window.renderRadarView = renderRadarView;

async function onRadarStudentChange(studentId) {
  const listCont = document.getElementById('radar-matches-list');
  if (!listCont) return;
  listCont.innerHTML = '<div class="loading-row"><span class="blink">▌</span> scanning opportunities…</div>';
  
  try {
    const res = await fetch(`/api/opportunities/${studentId}`);
    const matches = await res.json();
    
    listCont.innerHTML = '';
    if (matches.length === 0) {
      listCont.innerHTML = '<div class="loading-row">No matching opportunities found for this student.</div>';
      return;
    }
    
    matches.forEach(m => {
      const row = document.createElement('div');
      row.className = 'stu-row';
      row.style.gridTemplateColumns = '2fr 1fr 1fr 2fr';
      
      let dlHtml = '—';
      if (m.competition.deadline) {
        if (m.days_remaining !== null) {
          if (m.days_remaining < 0) {
            dlHtml = `<span style="color:var(--text-3);">Closed</span>`;
          } else {
            dlHtml = `<span style="color:${m.is_urgent ? 'var(--red)' : 'var(--text-2)'};">${m.competition.deadline}<br/><small style="font-family:var(--mono); font-size:0.6rem;">(${m.days_remaining} days left)</small></span>`;
          }
        } else {
          dlHtml = `<span>${m.competition.deadline}</span>`;
        }
      }
      
      const scoreColor = m.match_score >= 90 ? 'var(--green)' : m.match_score >= 70 ? 'var(--amber)' : 'var(--red)';
      
      row.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:4px;">
          <strong style="font-size:0.85rem; color:var(--text-1);">${m.competition.name}</strong>
          <span style="font-size:0.68rem; color:var(--text-3); font-family:var(--mono);">${m.competition.type} · ${m.competition.fee}</span>
        </div>
        <div style="font-size:0.75rem;">${dlHtml}</div>
        <div style="font-family:var(--mono); font-weight:700; color:${scoreColor}; font-size:0.85rem;">${m.match_score}% Match</div>
        <div style="font-size:0.72rem; color:var(--text-2); line-height:1.4;">${m.why}<br/><small style="color:var(--text-3); display:block; margin-top:2px;">${m.competition.description}</small></div>
      `;
      listCont.appendChild(row);
    });
  } catch (err) {
    console.error("Error loading opportunities:", err);
    listCont.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load opportunities</div>';
  }
}
window.onRadarStudentChange = onRadarStudentChange;

async function importCompetition() {
  const urlInput = document.getElementById('radar-import-url');
  const statusEl = document.getElementById('radar-import-status');
  if (!urlInput || !urlInput.value.trim()) return alert("Please enter a valid CompeteMap URL");
  
  const url = urlInput.value.trim();
  statusEl.style.display = 'block';
  statusEl.style.color = 'var(--text-2)';
  statusEl.innerHTML = '<span class="blink">▌</span> scraping and importing competition from CompeteMap…';
  
  try {
    const res = await fetch('/api/import_competition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const d = await res.json();
    if (res.ok) {
      statusEl.style.color = 'var(--green)';
      statusEl.innerHTML = `✓ Successfully imported <strong>${d.name}</strong>! Target tags: ${d.subject_tags.join(', ')}. Scanned and added to database.`;
      urlInput.value = '';
      
      // Refresh current student matches
      const sel = document.getElementById('radar-student-select');
      if (sel && sel.value) {
        onRadarStudentChange(sel.value);
      }
    } else {
      statusEl.style.color = 'var(--red)';
      statusEl.innerHTML = `✕ Import failed: ${d.error}`;
    }
  } catch (err) {
    statusEl.style.color = 'var(--red)';
    statusEl.innerHTML = `✕ Network error: ${err.message}`;
  }
}
window.importCompetition = importCompetition;

// ══════════════════════════════════════════════
//  COLLEGE SHORTLIST & DEADLINE CALENDAR
// ══════════════════════════════════════════════

let collegesList = [];
let calendarEvents = [];

async function renderShortlistView() {
  const sel = document.getElementById('shortlist-student-select');
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '';
  students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.name} (${s.id})`;
    sel.appendChild(opt);
  });
  if (currentVal && students.some(s => s.id === currentVal)) {
    sel.value = currentVal;
  } else if (students.length > 0) {
    sel.value = students[0].id;
  }
  
  if (collegesList.length === 0) {
    try {
      const res = await fetch('/api/colleges');
      collegesList = await res.json();
    } catch (e) {
      console.error(e);
    }
  }
  
  if (sel.value) {
    onShortlistStudentChange(sel.value);
  }
}
window.renderShortlistView = renderShortlistView;

function onShortlistStudentChange(studentId) {
  filterCollegesList();
}
window.onShortlistStudentChange = onShortlistStudentChange;

function filterCollegesList() {
  const sel = document.getElementById('shortlist-student-select');
  if (!sel || !sel.value) return;
  const studentId = sel.value;
  const student = students.find(s => s.id === studentId);
  if (!student) return;
  
  const query = document.getElementById('shortlist-search').value.toLowerCase().trim();
  const container = document.getElementById('colleges-grid-container');
  container.innerHTML = '';
  
  const shortlisted = student.shortlisted_colleges || [];
  let renderCount = 0;
  for (let i = 0; i < collegesList.length; i++) {
    const c = collegesList[i];
    const matchQuery = !query || 
      c.name.toLowerCase().includes(query) || 
      c.country.toLowerCase().includes(query) ||
      c.courses.some(crs => crs.toLowerCase().includes(query));
      
    if (!matchQuery) continue;
    
    const isShortlisted = shortlisted.includes(c.id);
    if (!isShortlisted && renderCount >= 50) continue;
    
    renderCount++;
    const card = document.createElement('div');
    card.className = 'form-card';
    card.style.padding = '18px';
    card.style.background = isShortlisted ? 'rgba(200,255,0,0.02)' : 'var(--surface)';
    card.style.border = isShortlisted ? '1px solid var(--accent)' : '1px solid var(--border)';
    card.style.margin = '0';
    
    let deadlinesHtml = '';
    c.deadlines.forEach(dl => {
      deadlinesHtml += `
        <div style="font-size:0.72rem; color:var(--text-2); margin-top:4px;">
          📅 <strong>${dl.label}:</strong> ${dl.date} <br/>
          <span style="font-size:0.65rem; color:var(--text-3);">${dl.description}</span>
        </div>`;
    });
    
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
        <div>
          <h3 style="font-size:1rem; font-weight:700; color:var(--text-1);">${c.name}</h3>
          <span style="font-family:var(--mono); font-size:0.68rem; color:var(--text-3); text-transform:uppercase;">${c.country}</span>
        </div>
        <button class="${isShortlisted ? 'btn-reset' : 'btn-run'}" onclick="toggleShortlistCollege('${c.id}')" style="padding:6px 14px; font-size:0.72rem;">
          ${isShortlisted ? 'remove shortlist' : 'shortlist college'}
        </button>
      </div>
      
      <div style="margin-bottom:10px; font-size:0.75rem;">
        <strong style="color:var(--text-3); font-family:var(--mono); font-size:0.6rem; text-transform:uppercase; display:block; margin-bottom:4px;">Popular Courses:</strong>
        <span style="color:var(--text-2);">${c.courses.join(', ')}</span>
      </div>
      
      ${c.subject_requirements ? `
      <div style="margin-bottom:10px; font-size:0.75rem;">
        <strong style="color:var(--text-3); font-family:var(--mono); font-size:0.6rem; text-transform:uppercase; display:block; margin-bottom:4px;">Subject Requirements:</strong>
        <span style="color:var(--text-2);">${c.subject_requirements.join(', ')}</span>
      </div>` : ''}
      
      <div style="margin-bottom:10px; font-size:0.75rem;">
        <strong style="color:var(--text-3); font-family:var(--mono); font-size:0.6rem; text-transform:uppercase; display:block; margin-bottom:4px;">Required Exams:</strong>
        <span style="font-family:var(--mono); font-weight:700; color:var(--amber);">${c.required_exams.join(', ')}</span>
      </div>

      ${c.expected_sat && c.expected_sat !== "N/A" && c.expected_sat !== "nan" ? `
      <div style="margin-bottom:10px; font-size:0.75rem;">
        <strong style="color:var(--text-3); font-family:var(--mono); font-size:0.6rem; text-transform:uppercase; display:block; margin-bottom:4px;">Expected SAT:</strong>
        <span style="font-family:var(--mono); font-weight:700; color:var(--green);">${c.expected_sat}</span>
      </div>` : ''}

      <div style="border-top:1px dashed var(--border); padding-top:8px;">
        <strong style="color:var(--text-3); font-family:var(--mono); font-size:0.6rem; text-transform:uppercase; display:block; margin-bottom:4px;">Admissions Deadlines:</strong>
        ${deadlinesHtml}
      </div>
    `;
    container.appendChild(card);
  }
}
window.filterCollegesList = filterCollegesList;

async function toggleShortlistCollege(collegeId) {
  const sel = document.getElementById('shortlist-student-select');
  if (!sel || !sel.value) return;
  const studentId = sel.value;
  const student = students.find(s => s.id === studentId);
  if (!student) return;
  
  let shortlisted = [...(student.shortlisted_colleges || [])];
  if (shortlisted.includes(collegeId)) {
    shortlisted = shortlisted.filter(id => id !== collegeId);
  } else {
    shortlisted.push(collegeId);
  }
  
  try {
    const res = await fetch(`/api/students/${studentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...student, shortlisted_colleges: shortlisted })
    });
    if (res.ok) {
      student.shortlisted_colleges = shortlisted;
      filterCollegesList();
      await refreshData();
    } else {
      alert("Failed to update shortlist.");
    }
  } catch (err) {
    console.error(err);
  }
}
window.toggleShortlistCollege = toggleShortlistCollege;

let currentCalYear = 2026;
let currentCalMonth = 6;
let selectedCalDay = null;

async function renderCalendarView() {
  const sel = document.getElementById('calendar-student-select');
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '';
  students.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.name} (${s.id})`;
    sel.appendChild(opt);
  });
  if (currentVal && students.some(s => s.id === currentVal)) {
    sel.value = currentVal;
  } else if (students.length > 0) {
    sel.value = students[0].id;
  }
  
  currentCalYear = 2026;
  currentCalMonth = 6;
  selectedCalDay = null;
  
  if (sel.value) {
    onCalendarStudentChange(sel.value);
  }
}
window.renderCalendarView = renderCalendarView;

async function onCalendarStudentChange(studentId) {
  const listCont = document.getElementById('calendar-events-list');
  if (!listCont) return;
  listCont.innerHTML = '<div class="loading-row"><span class="blink">▌</span> loading student deadlines calendar…</div>';
  
  try {
    const res = await fetch(`/api/calendar/${studentId}`);
    calendarEvents = await res.json();
    selectedCalDay = null;
    updateCalendarUI();
  } catch (err) {
    console.error("Error loading calendar:", err);
    listCont.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load deadlines calendar</div>';
  }
}
window.onCalendarStudentChange = onCalendarStudentChange;

function navigateCalendarMonth(direction) {
  currentCalMonth += direction;
  if (currentCalMonth < 0) {
    currentCalMonth = 11;
    currentCalYear -= 1;
  } else if (currentCalMonth > 11) {
    currentCalMonth = 0;
    currentCalYear += 1;
  }
  selectedCalDay = null;
  updateCalendarUI();
}
window.navigateCalendarMonth = navigateCalendarMonth;

function updateCalendarUI() {
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const lbl = document.getElementById('calendar-month-label');
  if (lbl) {
    lbl.textContent = `${months[currentCalMonth]} ${currentCalYear}`;
  }
  
  renderCalendarGrid();
  filterCalendarEvents();
}

function renderCalendarGrid() {
  const cellsCont = document.getElementById('calendar-grid-cells');
  if (!cellsCont) return;
  cellsCont.innerHTML = '';
  
  const firstDay = new Date(currentCalYear, currentCalMonth, 1).getDay();
  const totalDays = new Date(currentCalYear, currentCalMonth + 1, 0).getDate();
  
  for (let i = 0; i < firstDay; i++) {
    const pad = document.createElement('div');
    pad.style.height = '42px';
    cellsCont.appendChild(pad);
  }
  
  const showCollege = document.getElementById('cal-filter-college').checked;
  const showExam = document.getElementById('cal-filter-exam').checked;
  const showComp = document.getElementById('cal-filter-competition').checked;
  
  for (let day = 1; day <= totalDays; day++) {
    const cell = document.createElement('div');
    cell.style.height = '42px';
    cell.style.display = 'flex';
    cell.style.flexDirection = 'column';
    cell.style.alignItems = 'center';
    cell.style.justifyContent = 'space-between';
    cell.style.padding = '4px 2px';
    cell.style.background = 'var(--surface)';
    cell.style.border = '1px solid var(--border)';
    cell.style.borderRadius = '4px';
    cell.style.cursor = 'pointer';
    cell.style.fontSize = '0.72rem';
    cell.style.fontFamily = 'var(--mono)';
    cell.style.transition = 'all 0.15s ease';
    
    if (selectedCalDay === day) {
      cell.style.borderColor = 'var(--accent)';
      cell.style.background = 'rgba(200,255,0,0.04)';
    }
    
    const dayLabel = document.createElement('span');
    dayLabel.textContent = day;
    dayLabel.style.color = 'var(--text-1)';
    dayLabel.style.fontWeight = '600';
    cell.appendChild(dayLabel);
    
    const dayEvents = calendarEvents.filter(e => {
      const eDate = new Date(e.date);
      return eDate.getFullYear() === currentCalYear && 
             eDate.getMonth() === currentCalMonth && 
             eDate.getDate() === day;
    });
    
    const dotsCont = document.createElement('div');
    dotsCont.style.display = 'flex';
    dotsCont.style.gap = '3px';
    
    let hasCol = false, hasEx = false, hasCmp = false;
    dayEvents.forEach(e => {
      if (e.type === 'college' && showCollege) hasCol = true;
      if (e.type === 'exam' && showExam) hasEx = true;
      if (e.type === 'competition' && showComp) hasCmp = true;
    });
    
    if (hasCol) {
      const dot = document.createElement('span');
      dot.style.width = '5px';
      dot.style.height = '5px';
      dot.style.borderRadius = '50%';
      dot.style.background = 'var(--red)';
      dotsCont.appendChild(dot);
    }
    if (hasEx) {
      const dot = document.createElement('span');
      dot.style.width = '5px';
      dot.style.height = '5px';
      dot.style.borderRadius = '50%';
      dot.style.background = 'var(--amber)';
      dotsCont.appendChild(dot);
    }
    if (hasCmp) {
      const dot = document.createElement('span');
      dot.style.width = '5px';
      dot.style.height = '5px';
      dot.style.borderRadius = '50%';
      dot.style.background = 'var(--green)';
      dotsCont.appendChild(dot);
    }
    
    cell.appendChild(dotsCont);
    
    cell.onclick = () => {
      if (selectedCalDay === day) {
        selectedCalDay = null;
      } else {
        selectedCalDay = day;
      }
      updateCalendarUI();
    };
    
    cellsCont.appendChild(cell);
  }
}

function filterCalendarEvents() {
  const listCont = document.getElementById('calendar-events-list');
  if (!listCont) return;
  listCont.innerHTML = '';
  
  const showCollege = document.getElementById('cal-filter-college').checked;
  const showExam = document.getElementById('cal-filter-exam').checked;
  const showComp = document.getElementById('cal-filter-competition').checked;
  
  const currentContextDate = new Date("2026-07-25");
  
  const filtered = calendarEvents.filter(e => {
    if (e.type === 'college' && !showCollege) return false;
    if (e.type === 'exam' && !showExam) return false;
    if (e.type === 'competition' && !showComp) return false;
    
    const eDate = new Date(e.date);
    const matchMonth = eDate.getFullYear() === currentCalYear && eDate.getMonth() === currentCalMonth;
    if (!matchMonth) return false;
    
    if (selectedCalDay !== null && eDate.getDate() !== selectedCalDay) return false;
    return true;
  });
  
  if (filtered.length === 0) {
    listCont.innerHTML = `
      <div class="loading-row" style="color:var(--text-3);">
        No events found for ${selectedCalDay ? `Day ${selectedCalDay}` : 'this month'} matching filters.
      </div>
    `;
    return;
  }
  
  filtered.forEach(e => {
    const row = document.createElement('div');
    row.className = 'stu-row';
    row.style.gridTemplateColumns = '100px 2fr 120px 2fr';
    row.style.cursor = 'default';
    
    const eventDate = new Date(e.date);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const formattedDate = `${eventDate.getDate()} ${months[eventDate.getMonth()]}`;
    
    const diffTime = eventDate.getTime() - currentContextDate.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    let countdownHtml = '';
    if (diffDays < 0) {
      countdownHtml = `<span style="color:var(--text-3); font-size:0.6rem; display:block;">Passed</span>`;
    } else if (diffDays === 0) {
      countdownHtml = `<span style="color:var(--red); font-weight:700; font-size:0.6rem; display:block;">Today</span>`;
    } else {
      countdownHtml = `<span style="color:${diffDays <= 30 ? 'var(--red)' : 'var(--text-2)'}; font-size:0.6rem; display:block; font-weight:600;">In ${diffDays} days</span>`;
    }
    
    let badgeColor = 'var(--red)';
    let typeName = 'College';
    if (e.type === 'exam') {
      badgeColor = 'var(--amber)';
      typeName = 'Entrance Test';
    } else if (e.type === 'competition') {
      badgeColor = 'var(--green)';
      typeName = 'Olympiad/Contest';
    }
    
    const badgeHtml = `
      <span style="font-family:var(--mono); font-size:0.55rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; padding:2px 8px; border:1px solid ${badgeColor}; color:${badgeColor}; border-radius:12px;">
        ${typeName}
      </span>
    `;
    
    row.innerHTML = `
      <div>
        <strong style="color:var(--text-1); font-size:0.8rem; display:block;">${formattedDate}</strong>
        ${countdownHtml}
      </div>
      <div style="font-weight:700; color:var(--text-1); font-size:0.8rem; line-height:1.3;">${e.title}</div>
      <div>${badgeHtml}</div>
      <div style="font-size:0.72rem; color:var(--text-2); line-height:1.4;">${e.description}</div>
    `;
    listCont.appendChild(row);
  });
}
window.filterCalendarEvents = filterCalendarEvents;

