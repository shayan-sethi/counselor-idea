/* ═══════════════════════════════════════════════════
   PRISM — Student Portal Controller
   ═══════════════════════════════════════════════════ */

let targets = {};
let createdStudentId = null;
let selectedTargetIds = [];

const SUBJECTS = [
  "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
  "English", "Economics", "History", "Political Science", "Sociology",
  "Physical Education", "Fine Arts", "Business Studies", "Accountancy",
  "Applied Mathematics", "Hindi", "Geography"
];

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    const tRes = await fetch('/api/targets');
    targets = await tRes.json();
    populateForm();
  } catch (e) {
    console.error('Init error:', e);
  }
}

function populateForm() {
  // Subject checkboxes
  const subEl = document.getElementById('sf-subjects');
  subEl.innerHTML = '';
  SUBJECTS.forEach(sub => {
    const lbl = document.createElement('label');
    lbl.className = 'sc-label';
    lbl.innerHTML = `<input type="checkbox" value="${sub}" />${sub}`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
    subEl.appendChild(lbl);
  });

  console.log("Fetched targets:", targets);

  // Populate Target dropdown select
  const selectEl = document.getElementById('sf-targets-select');
  selectEl.innerHTML = '<option value="" disabled selected>Select a target pathway...</option>';
  let count = 0;
  for (const tid in targets) {
    const t = targets[tid];
    const opt = document.createElement('option');
    opt.value = tid;
    opt.textContent = t.name;
    selectEl.appendChild(opt);
    count++;
  }
  console.log(`Populated ${count} targets into select dropdown`);

  // Bind Add Button click handler dynamically
  const addBtn = document.getElementById('btn-add-target');
  if (addBtn) {
    addBtn.onclick = addTargetFromSelect;
  }

  // Render initial targets list
  renderSelectedTargets();
}

function addTargetFromSelect() {
  console.log("addTargetFromSelect called");
  const selectEl = document.getElementById('sf-targets-select');
  if (!selectEl) {
    console.error("selectEl not found in DOM");
    return;
  }
  console.log("Select element:", selectEl);
  console.log("Select options count:", selectEl.options.length);
  console.log("Selected index:", selectEl.selectedIndex);
  if (selectEl.selectedIndex >= 0) {
    const opt = selectEl.options[selectEl.selectedIndex];
    console.log("Selected option HTML:", opt.outerHTML);
    console.log("Selected option value:", opt.value);
    console.log("Selected option text:", opt.text);
  }
  const tid = selectEl.value;
  console.log("Selected target ID (via selectEl.value):", tid);
  if (!tid) {
    console.warn("No target ID selected");
    return;
  }
  if (!selectedTargetIds.includes(tid)) {
    selectedTargetIds.push(tid);
    console.log("Current selectedTargetIds:", selectedTargetIds);
    renderSelectedTargets();
  } else {
    console.log("Target already selected");
  }
  selectEl.value = ""; // Reset select
}

function removeTargetPathway(tid) {
  console.log("Removing target ID:", tid);
  selectedTargetIds = selectedTargetIds.filter(id => id !== tid);
  renderSelectedTargets();
}

// Expose to window for global access
window.addTargetFromSelect = addTargetFromSelect;
window.removeTargetPathway = removeTargetPathway;

function renderSelectedTargets() {
  console.log("renderSelectedTargets called, count:", selectedTargetIds.length);
  const listEl = document.getElementById('sf-selected-targets-list');
  listEl.innerHTML = '';
  if (selectedTargetIds.length === 0) {
    listEl.innerHTML = '<div style="color:var(--text-3); font-family:var(--mono); font-size:0.75rem; padding:8px 0;">No target pathways added yet.</div>';
    return;
  }
  selectedTargetIds.forEach(tid => {
    const t = targets[tid];
    console.log("Rendering target:", tid, t);
    if (!t) return;
    const row = document.createElement('div');
    row.className = 'selected-target-item';
    row.innerHTML = `
      <span>${t.name}</span>
      <button type="button" class="btn-delete-sm" onclick="removeTargetPathway('${tid}')">✕</button>
    `;
    listEl.appendChild(row);
  });
}

function showStep(step) {
  document.getElementById('step-profile').classList.toggle('hidden', step !== 'profile');
  document.getElementById('step-results').classList.toggle('hidden', step !== 'results');
  document.getElementById('tab-profile').classList.toggle('active', step === 'profile');
  document.getElementById('tab-results').classList.toggle('active', step === 'results');
}

function addStudentPortfolioRow(activity = '', desc = '', tier = 3) {
  const list = document.getElementById('sf-portfolio-list');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.innerHTML = `
    <input type="text" placeholder="activity name" class="pf-activity" value="${activity}" />
    <input type="text" placeholder="description" class="pf-desc" value="${desc}" />
    <select class="pf-tier">
      <option value="1" ${tier === 1 ? 'selected' : ''}>Tier 1</option>
      <option value="2" ${tier === 2 ? 'selected' : ''}>Tier 2</option>
      <option value="3" ${tier === 3 ? 'selected' : ''}>Tier 3</option>
    </select>
    <button type="button" class="btn-delete-sm" onclick="this.parentElement.remove()">✕</button>
  `;
  list.appendChild(row);
}

async function submitProfile(e) {
  e.preventDefault();

  const name = document.getElementById('sf-name').value.trim();
  const board = document.getElementById('sf-board').value;
  const classLevel = parseInt(document.getElementById('sf-class').value);

  const subjectCbs = document.querySelectorAll('#sf-subjects input:checked');
  const boardSubjects = [...subjectCbs].map(cb => cb.value);
  const tgts = selectedTargetIds;

  if (!name) return alert('Please enter your name');
  if (boardSubjects.length === 0) return alert('Please select at least one subject');
  if (tgts.length === 0) return alert('Please select at least one target pathway');

  const cuetRaw = document.getElementById('sf-cuet').value.trim();
  const cuetSubjects = cuetRaw ? cuetRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  const grades = {};
  const g10 = document.getElementById('sf-g10').value.trim();
  const g11 = document.getElementById('sf-g11').value.trim();
  const gexp = document.getElementById('sf-gexp').value.trim();
  if (g10) grades.class_10_aggregate = g10;
  if (g11) grades.class_11_aggregate = g11;
  if (gexp) grades.current_expected_board = gexp;

  const tests = {};
  const sat = document.getElementById('sf-sat').value;
  const ap = document.getElementById('sf-ap').value;
  if (sat) tests.SAT = parseInt(sat);
  if (ap) tests.AP_CALCULUS_BC = parseInt(ap);

  const portfolio = [];
  document.querySelectorAll('#sf-portfolio-list .portfolio-row').forEach(row => {
    const act = row.querySelector('.pf-activity').value.trim();
    const d = row.querySelector('.pf-desc').value.trim();
    const t = parseInt(row.querySelector('.pf-tier').value);
    if (act) portfolio.push({ activity: act, description: d, tier: t });
  });

  const btn = document.getElementById('sf-submit');
  btn.disabled = true;
  btn.textContent = 'analyzing…';

  try {
    const res = await fetch('/api/students', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, board, class_level: classLevel,
        board_subjects: boardSubjects,
        cuet_subjects: cuetSubjects,
        grades, standardized_tests: tests,
        portfolio, targets: tgts
      })
    });
    const data = await res.json();
    createdStudentId = data.student.id;

    // Render audit results
    renderAuditResults(data.student, data.audit);
    showStep('results');

  } catch (err) {
    console.error(err);
    alert('Submission failed. Is the server running?');
  } finally {
    btn.disabled = false;
    btn.textContent = 'submit & get audit results →';
  }
}

function renderAuditResults(student, audit) {
  document.getElementById('res-title').textContent = `Audit: ${student.name}`;
  document.getElementById('res-subtitle').textContent =
    `${student.id} · ${student.board} · class ${student.class_level} · ${student.board_subjects.join(', ')}`;

  const body = document.getElementById('res-body');
  body.innerHTML = '';

  // Summary strip
  let totalGaps = 0, compliantCount = 0, maxUrg = 0;
  for (const tid in audit.targets) {
    const t = audit.targets[tid];
    if (t.compliant) compliantCount++;
    else totalGaps += t.gaps.length;
    maxUrg = Math.max(maxUrg, t.urgency_score);
  }

  const summaryEl = document.createElement('div');
  summaryEl.className = 'metrics-strip';
  summaryEl.style.marginBottom = '28px';
  summaryEl.innerHTML = `
    <div class="metric"><span class="metric-num">${Object.keys(audit.targets).length}</span><span class="metric-lbl">targets</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num accent-g">${compliantCount}</span><span class="metric-lbl">compliant</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num accent-y">${totalGaps}</span><span class="metric-lbl">gaps found</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num ${maxUrg >= 35 ? 'accent-r' : maxUrg > 0 ? 'accent-y' : 'accent-g'}">${maxUrg}%</span><span class="metric-lbl">risk score</span></div>
  `;
  body.appendChild(summaryEl);

  // Per-target results
  for (const tid in audit.targets) {
    const t = audit.targets[tid];

    const block = document.createElement('div');
    block.className = 'target-block';
    block.style.marginBottom = '16px';

    block.innerHTML = `
      <div class="tb-header">
        <span class="tb-name">${t.target_name}</span>
        <span class="tb-badge ${t.compliant ? 'tb-pass' : 'tb-fail'}">${t.compliant ? 'pass' : t.gaps.length + ' gap' + (t.gaps.length > 1 ? 's' : '')}</span>
      </div>
    `;

    const bdy = document.createElement('div');
    bdy.className = 'tb-body';

    if (t.compliant) {
      bdy.innerHTML = '<div class="tb-ok">✔ all requirements verified — you\'re on track!</div>';
    } else {
      // Gaps
      t.gaps.forEach(g => {
        const ge = document.createElement('div');
        ge.className = 'gap-entry';
        ge.innerHTML = `
          <div class="ge-title">${g.subject || '—'}: ${g.description}</div>
          <div class="ge-meta">
            <strong>citation:</strong> ${g.citation}<br>
            <strong>severity:</strong> ${g.severity}
          </div>
        `;
        bdy.appendChild(ge);
      });

      // Remediations
      if (t.remediations && t.remediations.length > 0) {
        const remHeader = document.createElement('div');
        remHeader.className = 'rem-section-label';
        remHeader.textContent = 'what you can do:';
        bdy.appendChild(remHeader);

        t.remediations.forEach((r, i) => {
          const fc = r.feasibility === 'HIGH' ? 'rf-high' : r.feasibility === 'MEDIUM' ? 'rf-med' : 'rf-low';
          const re = document.createElement('div');
          re.className = 'rem-entry';
          re.innerHTML = `
            <div class="re-header">
              <span class="re-num">option ${i + 1}</span>
              <span class="re-feas ${fc}">${r.feasibility}</span>
            </div>
            <div class="re-text">${r.remediation}</div>
            <div class="re-detail"><strong>action:</strong> ${r.action_item}</div>
          `;
          bdy.appendChild(re);
        });
      }
    }

    block.appendChild(bdy);
    body.appendChild(block);
  }

  // Edit button
  const editBtn = document.createElement('button');
  editBtn.className = 'btn-reset';
  editBtn.textContent = '← edit my profile';
  editBtn.style.marginTop = '16px';
  editBtn.onclick = () => showStep('profile');
  body.appendChild(editBtn);
}
