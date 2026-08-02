/* ═══════════════════════════════════════════════════
   PRISM — Student Portal Controller
   ═══════════════════════════════════════════════════ */

let targets = {};
let createdStudentId = null;
let selectedTargetIds = [];

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
  const authed = await checkUserSession();
  if (!authed) return;

  try {
    const tRes = await fetch('/api/targets');
    if (tRes.status === 401 || tRes.status === 403) {
      window.location.href = '/static/login.html';
      return;
    }
    targets = await tRes.json();
    populateForm();

    const boardSelect = document.getElementById('sf-board');
    if (boardSelect) {
      boardSelect.addEventListener('change', updateSubjectsGrid);
    }
    const g10BoardSelect = document.getElementById('sf-g10-board');
    if (g10BoardSelect) {
      g10BoardSelect.addEventListener('change', updateG10Placeholders);
    }

    // Automatically load logged in student's profile
    if (currentUserRole === 'student' && currentUserStudentId) {
      createdStudentId = currentUserStudentId;
      const isComplete = await loadExistingStudentProfile(currentUserStudentId);
      if(isComplete) {
        showStep('dash');
        unlockTabs();
      } else {
        showStep('onboarding');
        lockTabs();
      }
    }
  } catch (e) {
    console.error('Init error:', e);
  }
}

async function loadExistingStudentProfile(studentId) {
  let isComplete = false;
  try {
    const res = await fetch(`/api/student/${studentId}`);
    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        alert('loadProfile: 401/403');
        // window.location.href = '/static/login.html';
        return false;
      }
      return false;
    }
    const s = await res.json();
    
    // Fill basic details
    document.getElementById('sf-name').value = s.name || '';
    document.getElementById('sf-board').value = s.board || 'CBSE';
    document.getElementById('sf-class').value = s.class_level || 12;
    
    updateSubjectsGrid();
    
    // Check subjects
    const subjects = s.board_subjects || [];
    document.querySelectorAll('#sf-subjects input').forEach(cb => {
      const checked = subjects.includes(cb.value);
      cb.checked = checked;
      cb.parentElement.classList.toggle('checked', checked);
    });
    
    updateSubjectGradesUI();
    
    // Fill subject grades
    const grades = s.grades || {};
    const subjectsGrades = grades.subjects || {};
    document.querySelectorAll('.sf-subj-mark').forEach(input => {
      const sub = input.dataset.subject;
      if (subjectsGrades[sub] !== undefined) {
        input.value = subjectsGrades[sub];
      }
    });
    
    // Fill Grade 10 details
    if (document.getElementById('sf-g10-board') && s.grades?.g10_board) {
      document.getElementById('sf-g10-board').value = s.grades.g10_board;
    }
    updateG10Placeholders();
    
    document.getElementById('sf-g10').value = s.grades?.class_10_aggregate || '';
    document.getElementById('sf-g11').value = s.grades?.class_11_aggregate || '';
    document.getElementById('sf-gexp').value = s.grades?.current_expected_board || '';
    
    // Populate Grade 10 subject marks
    const g10Container = document.getElementById('sf-g10-subject-grades-container');
    if (g10Container) {
      g10Container.innerHTML = '';
      const g10Subjs = s.grades?.class_10_subjects || {};
      const keys = Object.keys(g10Subjs).length > 0 ? Object.keys(g10Subjs) : DEFAULT_G10_SUBJECTS;
      keys.forEach(sub => {
        addG10SubjectRow(sub);
      });
      document.querySelectorAll('.sf-g10-subj-mark').forEach(input => {
        const sub = input.dataset.g10Subject;
        if (g10Subjs[sub] !== undefined) {
          input.value = g10Subjs[sub];
        }
      });
    }
    
    // Check targets
    selectedTargetIds = s.targets || [];
    renderSelectedTargets();
    
    // CUET
    document.getElementById('sf-cuet').value = (s.cuet_subjects || []).join(', ');
    
    // SAT
    document.getElementById('sf-sat').value = s.standardized_tests?.SAT || '';
    
    // APs
    selectedAPs = {};
    for (const key in AP_SUBJECTS) {
      if (s.standardized_tests && s.standardized_tests[key] !== undefined) {
        selectedAPs[key] = s.standardized_tests[key];
      }
    }
    renderAPs();
    
    // Extracurriculars
    document.getElementById('sf-portfolio-list').innerHTML = '';
    (s.portfolio || []).forEach(item => {
      addStudentPortfolioRow(item.activity, item.description, item.tier);
    });
    
    // Shortlisted Colleges
    shortlistedColleges = s.shortlisted_colleges || [];
    if (typeof renderShortlist === 'function') renderShortlist();
    
    // Shortlisted Exams
    shortlistedExams = s.shortlisted_exams || [];
    if (typeof renderExamsTab === 'function') renderExamsTab();

    if (s.board_subjects && s.board_subjects.length > 0 && s.grades && Object.keys(s.grades).length > 0) isComplete = true;
    if (isComplete) {
      populateDashboard(s);
    }
    return isComplete;
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

function populateDashboard(s) {
  if (!s) return;
  
  // Welcome Text
  const firstName = (s.name || 'Student').split(' ')[0];
  const welcomeEl = document.getElementById('dash-welcome-text');
  if (welcomeEl) welcomeEl.innerText = `Welcome back, ${firstName}!`;
  
  // Readiness Calculation
  let readiness = 10; // Base
  if (s.board) readiness += 10;
  if (s.board_subjects && s.board_subjects.length > 0) readiness += 20;
  if (s.grades && Object.keys(s.grades).length > 0) readiness += 20;
  if (s.standardized_tests && Object.keys(s.standardized_tests).length > 0) readiness += 10;
  if (s.targets && s.targets.length > 0) readiness += 10;
  if (s.portfolio && s.portfolio.length > 0) readiness += 20;
  
  readiness = Math.min(readiness, 100);
  
  const readiText = document.getElementById('dash-readiness-text');
  const readiBar = document.getElementById('dash-readiness-bar');
  if (readiText) readiText.innerText = `${readiness}%`;
  if (readiBar) readiBar.style.width = `${readiness}%`;
  
  // KPIs
  if (document.getElementById('dash-grade-value')) document.getElementById('dash-grade-value').innerText = s.grades?.current_expected_board || '—';
  if (document.getElementById('dash-sat-value')) document.getElementById('dash-sat-value').innerText = s.standardized_tests?.SAT || '—';
  if (document.getElementById('dash-activities-value')) document.getElementById('dash-activities-value').innerText = s.portfolio ? s.portfolio.length : '0';
  
  // Recent Activities
  const recentActContainer = document.getElementById('dash-recent-activities');
  if (recentActContainer) {
    recentActContainer.innerHTML = '';
    if (s.portfolio && s.portfolio.length > 0) {
      const recent = s.portfolio.slice(-3).reverse();
      recent.forEach(act => {
        const div = document.createElement('div');
        div.style.padding = '12px';
        div.style.background = 'var(--bg)';
        div.style.borderRadius = '8px';
        div.style.border = '1px solid var(--border)';
        div.innerHTML = `
          <div style="font-weight: 600; color: var(--text-1); font-size: 0.95rem;">${act.activity}</div>
          <div style="font-size: 0.85rem; color: var(--text-2); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${act.description}</div>
        `;
        recentActContainer.appendChild(div);
      });
    } else {
      recentActContainer.innerHTML = '<div style="color: var(--text-3); font-size: 0.9rem;">No activities logged yet.</div>';
    }
  }
  
  // Shortlisted Colleges
  const shortColContainer = document.getElementById('dash-shortlisted-colleges');
  if (shortColContainer) {
    shortColContainer.innerHTML = '';
    const sColleges = s.shortlisted_colleges || [];
    const tColleges = (s.targets || []).map(tid => targets[tid] ? targets[tid].university : null).filter(Boolean);
    const colleges = [...new Set([...sColleges, ...tColleges])];
    
    if (colleges.length > 0) {
      colleges.forEach(c => {
        const span = document.createElement('span');
        span.style.padding = '4px 10px';
        span.style.background = 'var(--accent-light)';
        span.style.color = 'var(--accent)';
        span.style.borderRadius = '12px';
        span.style.fontSize = '0.8rem';
        span.style.fontWeight = '600';
        span.innerText = c.replace(/_/g, ' ');
        shortColContainer.appendChild(span);
      });
    } else {
      shortColContainer.innerHTML = '<div style="color: var(--text-3); font-size: 0.9rem;">No colleges shortlisted yet.</div>';
    }
  }
  
  // Next Steps
  const nextStepsContainer = document.getElementById('dash-next-steps');
  if (nextStepsContainer) {
    nextStepsContainer.innerHTML = '';
    const steps = [];
    if (readiness < 100) steps.push("Complete your profile to unlock more insights.");
    if (!s.portfolio || s.portfolio.length < 3) steps.push("Log more extracurricular activities to strengthen your profile.");
    if (!s.shortlisted_colleges || s.shortlisted_colleges.length === 0) steps.push("Use the Opportunity Radar to shortlist colleges.");
    if (!s.standardized_tests || (!s.standardized_tests.SAT && !s.standardized_tests.ACT)) steps.push("Consider adding a standardized test score.");
    
    if (steps.length === 0) steps.push("Your profile looks great! Keep up the good work.");
    
    steps.forEach(step => {
      const li = document.createElement('li');
      li.style.display = 'flex';
      li.style.alignItems = 'flex-start';
      li.style.gap = '10px';
      li.style.fontSize = '0.9rem';
      li.style.color = 'var(--text-2)';
      li.innerHTML = `<svg width="16" height="16" style="margin-top: 2px; color: var(--accent); flex-shrink: 0;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg> ${step}`;
      nextStepsContainer.appendChild(li);
    });
  }
}


function getPlaceholderForBoard(board) {
  if (board === 'IB' || board === 'IB MYP') return "e.g. 7";
  if (board === 'IGCSE' || board === 'A-Levels') return "e.g. A*";
  return "e.g. 95";
}

function updateG10Placeholders() {
  const g10Board = document.getElementById('sf-g10-board')?.value;
  const ph = getPlaceholderForBoard(g10Board);
  document.querySelectorAll('.sf-g10-subj-mark').forEach(input => {
    input.placeholder = ph;
  });
}

let selectedUniversity = "";

function updateSubjectGradesUI() {
  const container = document.getElementById('sf-subject-grades-container');
  const section = document.getElementById('sf-subject-grades-section');
  if (!container || !section) return;

  const checkedCbs = document.querySelectorAll('#sf-subjects input:checked');
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
    const board = document.getElementById('sf-board').value;
    const ph = getPlaceholderForBoard(board);
    field.innerHTML = `
      <label style="font-size: 0.72rem; color: var(--text-2); margin-bottom: 4px; display: block;">${sub}</label>
      <input type="text" class="sf-subj-mark" data-subject="${sub}" placeholder="${ph}" value="${val}" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
    `;
    container.appendChild(field);
  });
}

function updateSubjectsGrid() {
  const board = document.getElementById('sf-board').value;
  const subjects = BOARD_SUBJECTS[board] || BOARD_SUBJECTS["CBSE"];

  // Student subjects checkboxes
  const subEl = document.getElementById('sf-subjects');
  subEl.innerHTML = '';
  subjects.forEach(sub => {
    const lbl = document.createElement('label');
    lbl.className = 'sc-label';
    lbl.innerHTML = `<input type="checkbox" value="${sub}" /><span>${sub}</span>`;
    const cb = lbl.querySelector('input');
    cb.addEventListener('change', () => {
      lbl.classList.toggle('checked', cb.checked);
      updateSubjectGradesUI();
    });
    subEl.appendChild(lbl);
  });

  // Compulsory subjects check-grid for custom targets
  const compEl = document.getElementById('sf-target-compulsory');
  if (compEl) {
    compEl.innerHTML = '';
    subjects.forEach(sub => {
      const lbl = document.createElement('label');
      lbl.className = 'sc-label';
      lbl.innerHTML = `<input type="checkbox" value="${sub}" /><span>${sub}</span>`;
      const cb = lbl.querySelector('input');
      cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
      compEl.appendChild(lbl);
    });
  }

  // Reset/update subject grades UI when board/subjects change
  updateSubjectGradesUI();
}

const DEFAULT_G10_SUBJECTS = ["Mathematics", "Science", "Social Science", "English", "Hindi / Second Language"];

function initG10Subjects() {
  const container = document.getElementById('sf-g10-subject-grades-container');
  if (!container) return;
  if (container.children.length > 0) return;

  DEFAULT_G10_SUBJECTS.forEach(sub => {
    addG10SubjectRow(sub);
  });
}

function addG10SubjectRow(subjectName = '') {
  const inputEl = document.getElementById('sf-g10-custom-subj');
  const sub = subjectName || (inputEl ? inputEl.value.trim() : '');
  if (!sub) return;

  const container = document.getElementById('sf-g10-subject-grades-container');
  if (!container) return;

  if (container.querySelector(`[data-g10-subject="${sub}"]`)) {
    if (inputEl) inputEl.value = '';
    return;
  }

  const field = document.createElement('div');
  field.className = 'field';
  field.style.marginBottom = '8px';
  const g10Board = document.getElementById('sf-g10-board')?.value;
  const ph = getPlaceholderForBoard(g10Board);
  field.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <label style="font-size: 0.72rem; color: var(--text-2); display: block;">${sub}</label>
      <button type="button" class="btn-delete-sm" onclick="this.closest('.field').remove()" style="font-size:0.65rem; padding: 0 4px;">✕</button>
    </div>
    <input type="text" class="sf-g10-subj-mark" data-g10-subject="${sub}" placeholder="${ph}" style="font-family: var(--mono); font-size: 0.75rem; padding: 6px; background: var(--surface); border: 1px solid var(--border); color: var(--text-1); width: 100%; border-radius: 4px;" />
  `;
  container.appendChild(field);
  if (inputEl && !subjectName) inputEl.value = '';
}

function addCustomBoardSubject() {
  const input = document.getElementById('sf-custom-subject-input');
  if (!input) return;
  const sub = input.value.trim();
  if (!sub) return;

  const subEl = document.getElementById('sf-subjects');
  if (!subEl) return;

  const lbl = document.createElement('label');
  lbl.className = 'sc-label checked';
  lbl.innerHTML = `<input type="checkbox" value="${sub}" checked />${sub}`;
  const cb = lbl.querySelector('input');
  cb.addEventListener('change', () => {
    lbl.classList.toggle('checked', cb.checked);
    updateSubjectGradesUI();
  });
  subEl.appendChild(lbl);

  input.value = '';
  updateSubjectGradesUI();
}

function populateForm() {
  updateSubjectsGrid();
  initG10Subjects();

  // Populate AP subjects select
  const apSelect = document.getElementById('sf-ap-subject');
  if (apSelect) {
    apSelect.innerHTML = '<option value="" disabled selected>Select AP Subject...</option>';
    for (const key in AP_SUBJECTS) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = AP_SUBJECTS[key];
      apSelect.appendChild(opt);
    }
  }

  // Render initial targets list
  renderSelectedTargets();
}

async function searchStudentUnis(val) {
  const container = document.getElementById("sf-uni-results");
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
    list.forEach(uniObj => {
      const uniName = uniObj.name;
      const uniCountry = uniObj.country;
      const div = document.createElement("div");
      div.className = "autocomplete-suggestion";
      div.textContent = `${uniName} (${uniCountry})`;
      div.onclick = () => {
        document.getElementById("sf-target-uni").value = uniName;
        selectedUniversity = uniName;
        container.classList.add("hidden");
        document.getElementById("sf-target-name").value = "";
        const trackSelect = document.getElementById("sf-target-track");
        if (trackSelect) {
            let found = false;
            for (let i = 0; i < trackSelect.options.length; i++) {
                if (trackSelect.options[i].value === uniCountry) {
                    trackSelect.value = uniCountry;
                    found = true;
                    break;
                }
            }
            if (!found) trackSelect.value = "UK";
        }
      };
      container.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

async function searchStudentCourses(val) {
  const container = document.getElementById("sf-course-results");
  if (!selectedUniversity) {
    alert("Please select a university first");
    document.getElementById("sf-target-name").value = "";
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
      div.textContent = `${course.title} (${course.subject_group || 'N/A'})`;
      div.onclick = () => {
        document.getElementById("sf-target-name").value = course.title;
        container.classList.add("hidden");
      };
      container.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

async function createAndAddTarget() {
  const name = document.getElementById('sf-target-name').value.trim();
  const university = document.getElementById('sf-target-uni').value.trim();
  const track = document.getElementById('sf-target-track').value;
  const portfolio_tier = parseInt(document.getElementById('sf-target-portfolio').value);

  if (!name || !university) {
    alert("Please fill in both University and Course Name");
    return;
  }

  const checkedComp = document.querySelectorAll('#sf-target-compulsory input:checked');
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

  const btn = document.getElementById('btn-create-add-target');
  btn.disabled = true;
  btn.textContent = 'adding…';

  try {
    const res = await fetch('/api/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const tData = await res.json();
      targets[tData.id] = tData;

      if (!selectedTargetIds.includes(tData.id)) {
        selectedTargetIds.push(tData.id);
      }
      renderSelectedTargets();

      // Reset the target form inputs
      document.getElementById('sf-target-name').value = "";
      document.getElementById('sf-target-uni').value = "";
      document.getElementById('sf-target-track').value = "UK";
      document.getElementById('sf-target-portfolio').value = "3";
      document.querySelectorAll('#sf-target-compulsory input').forEach(cb => {
        cb.checked = false;
        cb.parentElement.classList.remove('checked');
      });
      selectedUniversity = "";
    } else {
      alert('Failed to save pathway to backend');
    }
  } catch (err) {
    console.error(err);
    alert('Network error when adding pathway');
  } finally {
    btn.disabled = false;
    btn.textContent = '+ add pathway';
  }
}

function removeTargetPathway(tid) {
  selectedTargetIds = selectedTargetIds.filter(id => id !== tid);
  renderSelectedTargets();
}

let selectedAPs = {};

function addAPRow(key, score) {
  const container = document.getElementById('sf-ap-list');
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.style.gridTemplateColumns = '2fr 1fr auto';
  row.style.marginBottom = '4px';
  row.style.alignItems = 'center';

  const subjectsMap = {
    "AP_CALCULUS_BC": "AP Calculus BC",
    "AP_CALCULUS_AB": "AP Calculus AB",
    "AP_PHYSICS_C_MECH": "AP Physics C: Mechanics",
    "AP_PHYSICS_C_EM": "AP Physics C: Elec & Mag",
    "AP_CHEMISTRY": "AP Chemistry",
    "AP_COMPUTER_SCIENCE_A": "AP Computer Science A",
    "AP_ENGLISH_LANG": "AP English Language",
    "AP_ENGLISH_LIT": "AP English Literature"
  };

  row.innerHTML = `
    <span style="font-family:var(--sans); font-size:0.8rem; color:var(--text-1);">${subjectsMap[key] || key}</span>
    <span style="font-family:var(--mono); font-size:0.8rem; color:var(--accent); font-weight:600;">Score: ${score}</span>
    <button type="button" class="btn-delete-sm" onclick="removeAP('${key}')">✕</button>
  `;
  container.appendChild(row);
}

function renderAPs() {
  const container = document.getElementById('sf-ap-list');
  container.innerHTML = '';
  for (const key in selectedAPs) {
    addAPRow(key, selectedAPs[key]);
  }
}

function addAPFromSelect() {
  const subEl = document.getElementById('sf-ap-subject');
  const scoreEl = document.getElementById('sf-ap-score');
  const key = subEl.value;
  const score = parseInt(scoreEl.value);

  if (!key) {
    alert("Please select an AP subject first");
    return;
  }

  selectedAPs[key] = score;
  renderAPs();

  // Reset dropdown
  subEl.value = "";
}

function removeAP(key) {
  delete selectedAPs[key];
  renderAPs();
}

async function animateAgentTrace(traceMap, callback) {
  const card = document.getElementById('agent-console-card');
  const term = document.getElementById('terminal-content');
  if (!card || !term) return callback();

  card.classList.remove('hidden');
  term.innerHTML = '';

  // Tool name to human-readable description mapping
  const TOOL_LABELS = {
    'fetch_student': 'Loading your profile...',
    'fetch_requirements': 'Analyzing target requirements...',
    'check_subjects': 'Checking subject prerequisites...',
    'check_grades': 'Verifying academic scores...',
    'check_timeline': 'Checking application deadlines...',
    'check_portfolio': 'Evaluating your extracurriculars...',
    'draft_remediations': 'Generating improvement suggestions...'
  };

  function humanizeObservation(obs) {
    try {
      const parsed = JSON.parse(obs);
      if (Array.isArray(parsed)) {
        if (parsed.length === 0) return '✓ No issues found.';
        return `Found ${parsed.length} item${parsed.length > 1 ? 's' : ''} to review.`;
      }
      if (parsed.name) return `Profile loaded: ${parsed.name}`;
      if (parsed.id) return `Requirements loaded for ${parsed.name || parsed.id}`;
      return obs.substring(0, 120) + (obs.length > 120 ? '...' : '');
    } catch {
      return obs.substring(0, 120) + (obs.length > 120 ? '...' : '');
    }
  }

  // Combine all traces from different targets
  let combinedTrace = [];
  for (const tid in traceMap) {
    combinedTrace.push({ type: 'header', message: `Evaluating pathway: ${tid.replace(/_/g, ' ')}` });
    combinedTrace = combinedTrace.concat(traceMap[tid]);
  }

  if (combinedTrace.length === 0) {
    combinedTrace.push({ type: 'thought', message: 'Initializing compliance evaluation...' });
    combinedTrace.push({ type: 'action', message: 'call_tool: check_subjects' });
    combinedTrace.push({ type: 'observation', message: '[]' });
  }

  for (let i = 0; i < combinedTrace.length; i++) {
    const log = combinedTrace[i];
    const line = document.createElement('div');
    line.style.marginBottom = '6px';

    if (log.type === 'header') {
      line.style.color = '#7aa2f7';
      line.style.fontWeight = 'bold';
      line.style.marginTop = '8px';
      line.textContent = log.message;
    } else if (log.type === 'thought') {
      // Skip raw thoughts — they're mostly redundant with humanized actions
      continue;
    } else if (log.type === 'action') {
      const toolName = log.message.replace('call_tool: ', '');
      const humanLabel = TOOL_LABELS[toolName] || `Running ${toolName}...`;
      line.innerHTML = `<span style="color: #7dcfff;">${humanLabel}</span>`;
    } else if (log.type === 'observation') {
      const summary = humanizeObservation(log.message);
      line.innerHTML = `<span style="color: #565f89; padding-left: 16px;">→ ${summary}</span>`;
    }

    term.appendChild(line);
    term.parentElement.scrollTop = term.parentElement.scrollHeight;
    await new Promise(r => setTimeout(r, 450));
  }

  const line = document.createElement('div');
  line.style.color = '#9ece6a';
  line.style.fontWeight = 'bold';
  line.style.marginTop = '12px';
  line.innerHTML = `✔ Analysis complete. Loading your results...`;
  term.appendChild(line);
  term.parentElement.scrollTop = term.parentElement.scrollHeight;

  await new Promise(r => setTimeout(r, 800));
  callback();
}

// Expose functions globally
window.searchStudentUnis = searchStudentUnis;
window.searchStudentCourses = searchStudentCourses;
window.createAndAddTarget = createAndAddTarget;
window.removeTargetPathway = removeTargetPathway;
window.addAPFromSelect = addAPFromSelect;
window.removeAP = removeAP;
window.animateAgentTrace = animateAgentTrace;

function renderSelectedTargets() {
  const listEl = document.getElementById('sf-selected-targets-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  if (selectedTargetIds.length === 0) {
    listEl.innerHTML = '<div style="color:var(--text-3); font-family:var(--mono); font-size:0.75rem; padding:8px 0;">No target pathways added yet.</div>';
    return;
  }
  selectedTargetIds.forEach(tid => {
    const t = targets[tid];
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
  const sp = document.getElementById('step-onboarding'); if (sp) { sp.classList.toggle('hidden', step !== 'onboarding'); sp.style.display = (step === 'onboarding') ? 'block' : 'none'; }
  const sd = document.getElementById('step-dash'); if (sd) { sd.classList.toggle('hidden', step !== 'dash'); sd.style.display = (step === 'dash') ? 'block' : 'none'; }
  document.getElementById('step-results').classList.toggle('hidden', step !== 'results');
  const rEl = document.getElementById('step-radar');
  if (rEl) rEl.classList.toggle('hidden', step !== 'radar');
  const slEl = document.getElementById('step-shortlist');
  if (slEl) slEl.classList.toggle('hidden', step !== 'shortlist');
  const cEl = document.getElementById('step-calendar');
  if (cEl) cEl.classList.toggle('hidden', step !== 'calendar');
  const schEl = document.getElementById('step-scholarships');
  if (schEl) schEl.classList.toggle('hidden', step !== 'scholarships');
  const recEl = document.getElementById('step-recycling');
  if (recEl) recEl.classList.toggle('hidden', step !== 'recycling');

  const tp = document.getElementById('tab-dash'); if (tp) tp.classList.toggle('active', step === 'dash');
  const tonb = document.getElementById('tab-onboarding'); if(tonb) tonb.classList.toggle('active', step === 'onboarding');
  document.getElementById('tab-results').classList.toggle('active', step === 'results');
  const rTab = document.getElementById('tab-radar');
  if (rTab) rTab.classList.toggle('active', step === 'radar');
  const slTab = document.getElementById('tab-shortlist');
  if (slTab) slTab.classList.toggle('active', step === 'shortlist');
  const cTab = document.getElementById('tab-calendar');
  if (cTab) cTab.classList.toggle('active', step === 'calendar');
  const schTab = document.getElementById('tab-scholarships');
  if (schTab) schTab.classList.toggle('active', step === 'scholarships');
  const recTab = document.getElementById('tab-recycling');
  if (recTab) recTab.classList.toggle('active', step === 'recycling');

  const advisorCard = document.getElementById('ai-advisor-card');
  if (advisorCard && step !== 'results') {
    advisorCard.classList.add('hidden');
  }

  if (step === 'radar') {
    renderStudentRadar();
  } else if (step === 'scholarships') {
    renderStudentScholarships();
  }
  if (step === 'shortlist') {
    renderStudentShortlist();
  } else if (step === 'recycling') {
    renderStudentRecyclingView();
  }
  if (step === 'calendar') {
    renderStudentCalendar();
  }
}

function addStudentPortfolioRow(activity = '', desc = '', tier = 3) {
  const list = document.getElementById('sf-portfolio-list');
  if (!list) return;
  const row = document.createElement('div');
  row.className = 'portfolio-row';
  row.style.display = 'grid';
  row.style.gridTemplateColumns = '1fr 2.5fr auto';
  row.style.gap = '8px';
  row.style.marginBottom = '8px';
  const safeAct = (activity || '').replace(/"/g, '&quot;');
  const safeDesc = (desc || '').replace(/"/g, '&quot;');
  row.innerHTML = `
    <input type="text" placeholder="activity name" class="pf-activity" value="${safeAct}" style="font-size:0.8rem; padding:6px; background:var(--surface); border:1px solid var(--border); color:var(--text-1); border-radius:4px;" />
    <input type="text" placeholder="describe what you did, awards won, level reached" class="pf-desc" value="${safeDesc}" style="font-size:0.8rem; padding:6px; background:var(--surface); border:1px solid var(--border); color:var(--text-1); border-radius:4px;" />
    <button type="button" class="btn-delete-sm" onclick="this.parentElement.remove()" style="padding:4px 8px;">✕</button>
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

  if (!name) return alert('Please enter your name');
  if (boardSubjects.length === 0) return alert('Please select at least one subject');

  const cuetRaw = document.getElementById('sf-cuet').value.trim();
  const cuetSubjects = cuetRaw ? cuetRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  const grades = {};
  const g10Board = document.getElementById('sf-g10-board')?.value;
  if (g10Board) grades.g10_board = g10Board;
  const g10 = document.getElementById('sf-g10').value.trim();
  const g11 = document.getElementById('sf-g11').value.trim();
  const gexp = document.getElementById('sf-gexp').value.trim();
  if (g10) grades.class_10_aggregate = g10;
  if (g11) grades.class_11_aggregate = g11;
  if (gexp) grades.current_expected_board = gexp;

  const g10SubjectsGrades = {};
  document.querySelectorAll('.sf-g10-subj-mark').forEach(input => {
    const mark = input.value.trim();
    if (mark) {
      g10SubjectsGrades[input.dataset.g10Subject] = mark;
    }
  });
  grades.class_10_subjects = g10SubjectsGrades;

  const subjectsGrades = {};
  document.querySelectorAll('.sf-subj-mark').forEach(input => {
    const mark = input.value.trim();
    if (mark) {
      subjectsGrades[input.dataset.subject] = mark;
    }
  });
  grades.subjects = subjectsGrades;

  const tests = {};
  const sat = document.getElementById('sf-sat').value;
  if (sat) tests.SAT = parseInt(sat);
  for (const apKey in selectedAPs) {
    tests[apKey] = selectedAPs[apKey];
  }

  const portfolio = [];
  document.querySelectorAll('#sf-portfolio-list .portfolio-row').forEach(row => {
    const act = row.querySelector('.pf-activity').value.trim();
    const d = row.querySelector('.pf-desc').value.trim();
    if (act) portfolio.push({ activity: act, description: d });
  });

  const btn = document.getElementById('sf-submit');
  btn.disabled = true;
  btn.textContent = 'analyzing…';

  try {
    let studentData;
    const payload = {
      name, board, class_level: classLevel,
      board_subjects: boardSubjects,
      cuet_subjects: cuetSubjects,
      grades, standardized_tests: tests,
      portfolio, targets: selectedTargetIds
    };

    if (createdStudentId) {
      const res = await fetch(`/api/students/${createdStudentId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        let errStr;
        try { errStr = await res.text(); } catch(e) { errStr = res.statusText; }
        alert(`Error from server (PUT ${res.status}): ${errStr}`);
        return;
        const data = await res.json();
        alert(`Error from server: ${data.error || JSON.stringify(data)}`);
        return;
      }
      studentData = (await res.json()).student;
    } else {
      const res = await fetch('/api/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        let errStr;
        try { errStr = await res.text(); } catch(e) { errStr = res.statusText; }
        alert(`Error from server (POST ${res.status}): ${errStr}`);
        return;
        const data = await res.json();
        alert(`Error from server: ${data.error || JSON.stringify(data)}`);
        return;
      }
      studentData = (await res.json()).student;
      createdStudentId = studentData.id;
    }

    // Now evaluate via /api/evaluate
    const evalRes = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: createdStudentId })
    });
    if (!evalRes.ok) {
      let errStr;
      try { errStr = await evalRes.text(); } catch(e) { errStr = evalRes.statusText; }
      alert(`Error during evaluation (${evalRes.status}): ${errStr}`);
      return;
    }
    const data = await evalRes.json();

    // Show step dash immediately
    alert('Profile successfully submitted!');
    unlockTabs();
    showStep('dash');
    const sRes = await fetch(`/api/student/${createdStudentId}`);
    if (sRes.ok) {
      const sData = await sRes.json();
      populateDashboard(sData);
    }

    // Fade the audit results body while terminal prints
    const resBody = document.getElementById('res-body');
    if (resBody) {
      resBody.style.opacity = '0.15';
      resBody.style.pointerEvents = 'none';
    }

    await animateAgentTrace(data.traces || {}, () => {
      if (resBody) {
        resBody.style.opacity = '1';
        resBody.style.pointerEvents = 'auto';
      }
      fetchStudentAudit();
    });

  } catch (err) {
    console.error(err);
    alert('Error saving profile');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit Profile →';
  }
}

function renderAuditResults(student, audit) {
  document.getElementById('res-title').textContent = `Audit: ${student.name}`;
  document.getElementById('res-subtitle').textContent =
    `${student.id} · ${student.board} · class ${student.class_level} · ${student.board_subjects.join(', ')}`;

  const body = document.getElementById('res-body');
  body.innerHTML = '';

  // Summary strip
  let totalGaps = 0, avgMatch = 0, targetCount = 0, maxUrg = 0;
  for (const tid in audit.targets) {
    const t = audit.targets[tid];
    totalGaps += (t.gaps || []).length;
    avgMatch += (t.match_score || 100);
    maxUrg = Math.max(maxUrg, t.urgency_score || 0);
    targetCount++;
  }
  avgMatch = targetCount > 0 ? Math.round(avgMatch / targetCount) : 100;

  const matchColor = avgMatch >= 90 ? 'accent-g' : avgMatch >= 70 ? 'accent-y' : 'accent-r';

  const summaryEl = document.createElement('div');
  summaryEl.className = 'metrics-strip';
  summaryEl.style.marginBottom = '28px';
  summaryEl.innerHTML = `
    <div class="metric"><span class="metric-num">${targetCount}</span><span class="metric-lbl">targets</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num ${matchColor}">${avgMatch}%</span><span class="metric-lbl">avg match</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num accent-y">${totalGaps}</span><span class="metric-lbl">gaps found</span></div>
    <div class="metric-div"></div>
    <div class="metric"><span class="metric-num ${maxUrg >= 35 ? 'accent-r' : maxUrg > 0 ? 'accent-y' : 'accent-g'}">${maxUrg}%</span><span class="metric-lbl">risk score</span></div>
  `;
  body.appendChild(summaryEl);

  if (targetCount === 0) {
    const empty = document.createElement('div');
    empty.className = 'loading-row';
    empty.style.marginTop = '16px';
    empty.textContent = 'No target pathways assigned yet — add colleges to your shortlist and your counselor will set up a compliance audit against them.';
    body.appendChild(empty);
  }

  // Per-target results
  for (const tid in audit.targets) {
    const t = audit.targets[tid];
    const ms = t.match_score || 100;
    const rl = t.risk_level || 'Strong Match';
    const badgeColor = ms >= 90 ? 'tb-pass' : ms >= 70 ? 'tb-warn' : 'tb-fail';

    const diffLabel = t.difficulty_label || 'Target';
    const diffBadge = diffLabel === 'Safety' ? 'tb-pass' : diffLabel === 'Target' ? 'tb-warn' : 'tb-fail';

    const block = document.createElement('div');
    block.className = 'target-block';
    block.style.marginBottom = '16px';

    block.innerHTML = `
      <div class="tb-header" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
        <span class="tb-name">${t.target_name}</span>
        <div style="display: flex; gap: 6px;">
          <span class="tb-badge ${badgeColor}">${ms}% Match · ${rl}</span>
          <span class="tb-badge ${diffBadge}" style="text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">${diffLabel}</span>
        </div>
      </div>
    `;

    const bdy = document.createElement('div');
    bdy.className = 'tb-body';

    if (t.compliant) {
      bdy.innerHTML = '<div class="tb-ok">✔ All requirements verified — you\'re on track!</div>';
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

    // Data freshness footer
    const verified = (t.gaps && t.gaps.length > 0 && t.gaps[0].last_verified)
      ? t.gaps[0].last_verified : null;
    if (verified) {
      const freshness = document.createElement('div');
      freshness.style.cssText = 'font-size: 0.7rem; color: var(--text-3); margin-top: 10px; font-style: italic;';
      freshness.textContent = `Requirements data last verified: ${verified}`;
      bdy.appendChild(freshness);
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

  // Set advisor state and show chat card
  currentAdvisorStudentId = student.id;
  const advisorCard = document.getElementById('ai-advisor-card');
  if (advisorCard) {
    advisorCard.classList.remove('hidden');
  }
}

let currentAdvisorStudentId = null;

async function sendStudentAdvisorMessage() {
  const input = document.getElementById('sf-chat-input');
  if (!input) return;
  const msg = input.value.trim();
  if (!msg) return;

  const chatContainer = document.getElementById('ai-advisor-chat');
  if (!chatContainer) return;

  // Append user message
  const userMsg = document.createElement('div');
  userMsg.style.cssText = 'margin-bottom: 8px; text-align: right;';
  userMsg.innerHTML = `<span style="background: var(--border); padding: 6px 12px; border-radius: 4px; display: inline-block; max-width: 80%; text-align: left; color: var(--text-1); font-family: var(--sans);">You: ${msg}</span>`;
  chatContainer.appendChild(userMsg);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  input.value = '';

  // Show thinking status
  const loadingMsg = document.createElement('div');
  loadingMsg.style.cssText = 'margin-bottom: 8px; font-style: italic; color: var(--text-3); font-size: 0.75rem;';
  loadingMsg.textContent = 'Advisor Agent is thinking...';
  chatContainer.appendChild(loadingMsg);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  try {
    const res = await fetch('/api/student_advisor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: currentAdvisorStudentId,
        message: msg
      })
    });
    const data = await res.json();
    loadingMsg.remove();

    // Render markdown format
    const agentMsg = document.createElement('div');
    agentMsg.style.cssText = 'margin-bottom: 12px; border-left: 2px solid var(--amber); padding-left: 8px; font-family: var(--sans);';

    let html = data.reply
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    agentMsg.innerHTML = `<strong style="color:var(--amber);">unlockED Copilot:</strong><br>${html}`;
    chatContainer.appendChild(agentMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  } catch (err) {
    loadingMsg.textContent = 'Error contacting advisor agent.';
  }
}

window.sendStudentAdvisorMessage = sendStudentAdvisorMessage;

/* ═══════════════════════════════════════════════════
   AUTOMATED AGENTIC DATA INGESTION HANDLERS
   ═══════════════════════════════════════════════════ */

let selectedIngestFiles = [];

function handleFileSelect(event) {
  const files = Array.from(event.target.files);
  selectedIngestFiles = files;
  const listEl = document.getElementById('file-list-preview');
  if (listEl) {
    if (files.length === 0) {
      listEl.innerHTML = '';
    } else {
      listEl.innerHTML = 'Selected Files: ' + files.map(f => `<strong>${f.name}</strong> (${(f.size / 1024).toFixed(1)} KB)`).join(', ');
    }
  }
}
window.handleFileSelect = handleFileSelect;

async function uploadAndIngestDocuments() {
  const fileInput = document.getElementById('ingest-file-input');
  const files = fileInput ? fileInput.files : [];
  const statusEl = document.getElementById('ingest-status');
  const btnEl = document.getElementById('btn-auto-ingest');

  if (!files || files.length === 0) {
    alert('Please select at least one transcript or resume file to ingest.');
    return;
  }

  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.style.color = 'var(--amber)';
    statusEl.innerHTML = 'Parsing documents... Extracting academic grades, board subjects, test scores, and extracurricular activities via unlockED AI.';
  }

  if (btnEl) btnEl.disabled = true;

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  formData.append('auto_save', 'true');

  try {
    const response = await fetch('/api/ingest_documents', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to parse documents.');
    }

    const s = data.student;

    // Auto-populate Name, Board, Class
    if (s.name) document.getElementById('sf-name').value = s.name;
    if (s.board) document.getElementById('sf-board').value = s.board;
    if (s.class_level) {
      document.getElementById('sf-class').value = s.class_level;
      if (typeof onClassChange === 'function') onClassChange();
    }

    // Auto-populate Expected Grade
    if (s.grades && s.grades.current_expected_board) {
      const expInput = document.getElementById('sf-expected-board');
      if (expInput) expInput.value = s.grades.current_expected_board.replace('%', '');
    }

    // Auto-populate SAT score
    if (s.standardized_tests && s.standardized_tests.SAT) {
      const satInput = document.getElementById('sf-sat');
      if (satInput) satInput.value = s.standardized_tests.SAT;
    }

    // Check detected subjects
    const allDetectedSubs = [...(s.board_subjects || []), ...(s.planned_class_11_subjects || [])];
    if (allDetectedSubs.length > 0) {
      const checkboxes = document.querySelectorAll('#sf-subjects input[type="checkbox"], #sf-planned-subjects input[type="checkbox"]');
      checkboxes.forEach(cb => {
        const valLower = cb.value.toLowerCase();
        if (allDetectedSubs.some(sub => valLower.includes(sub.toLowerCase()) || sub.toLowerCase().includes(valLower))) {
          cb.checked = true;
        }
      });
    }

    // Auto-populate Grade 10 Subject Scores with converted percentages
    const g10Subs = s.grades ? (s.grades.g10_subjects || s.grades.grade_10_subjects || s.grades.subjects) : null;
    if (g10Subs) {
      for (const [subName, subMark] of Object.entries(g10Subs)) {
        if (typeof addG10SubjectRow === 'function') addG10SubjectRow(subName);
        const subInput = document.querySelector(`.sf-g10-subj-mark[data-g10-subject="${subName}"]`);
        if (subInput && subMark) {
          subInput.value = typeof subMark === 'number' ? subMark : parseFloat(subMark) || 95;
        }
      }
    }

    // Populate Portfolio Activities into #sf-portfolio-list
    if (s.portfolio && s.portfolio.length > 0) {
      const listContainer = document.getElementById('sf-portfolio-list');
      if (listContainer) listContainer.innerHTML = '';
      s.portfolio.forEach(item => {
        if (typeof addStudentPortfolioRow === 'function') {
          addStudentPortfolioRow(item.activity, item.description, item.tier || 1);
        }
      });
    }

    if (statusEl) {
      statusEl.style.color = 'var(--green)';
      statusEl.innerHTML = `Ingestion Successful: Auto-populated profile for <strong>${s.name || 'Student'}</strong> from ${data.extracted_from.join(', ')}.`;
    }

    createdStudentId = s.id;

    // If targets were evaluated, show audit results automatically
    if (data.evaluation && data.evaluation.targets && Object.keys(data.evaluation.targets).length > 0) {
      renderAuditResults(data.student, data.evaluation);
    }

  } catch (err) {
    if (statusEl) {
      statusEl.style.color = 'var(--red)';
      statusEl.innerHTML = `Ingestion Failed: ${err.message}`;
    }
  } finally {
    if (btnEl) btnEl.disabled = false;
  }
}
window.uploadAndIngestDocuments = uploadAndIngestDocuments;

// ══════════════════════════════════════════════
//  OPPORTUNITY RADAR
// ══════════════════════════════════════════════

async function renderStudentRadar() {
  const body = document.getElementById('radar-body');
  if (!body) return;

  if (!createdStudentId) {
    body.innerHTML = '<div class="loading-row"><span class="blink">▌</span> submit your profile first to unlock radar matches</div>';
    return;
  }

  body.innerHTML = '<div class="loading-row"><span class="blink">▌</span> scanning opportunities…</div>';

  try {
    const res = await fetch(`/api/opportunities/${createdStudentId}`);
    const matches = await res.json();

    if (matches.length === 0) {
      body.innerHTML = '<div class="loading-row">No matching opportunities found for your current profile. Try adjusting target pathways or subjects.</div>';
      return;
    }

    let html = `
      <div style="display: flex; flex-direction: column; gap: 16px; margin-top: 20px;">
    `;

    matches.forEach(m => {
      let dlHtml = '—';
      if (m.competition.deadline) {
        if (m.days_remaining !== null) {
          if (m.days_remaining < 0) {
            dlHtml = `<span style="color:var(--text-3);">Closed</span>`;
          } else {
            dlHtml = `<span style="color:${m.is_urgent ? 'var(--red)' : 'var(--text-2)'}; font-weight:600;">${m.competition.deadline}<br/><small style="color:var(--text-3); font-size:0.7rem;">(${m.days_remaining} days left)</small></span>`;
          }
        } else {
          dlHtml = `<span>${m.competition.deadline}</span>`;
        }
      }

      const scoreColor = m.match_score >= 90 ? 'var(--green)' : m.match_score >= 70 ? 'var(--amber)' : 'var(--red)';

      html += `
        <div style="background: var(--surface); border: 1px solid var(--border); padding: 20px; border-radius: 12px; display: grid; grid-template-columns: 2fr 1fr 1fr 2.5fr; gap: 20px; align-items: start;">
          <div>
            <strong style="font-size:1rem; color:var(--text-1); display:block; margin-bottom:4px;">${m.competition.name}</strong>
            <span style="font-size:0.8rem; color:var(--text-3);">${m.competition.type} · ${m.competition.fee}</span>
          </div>
          <div style="font-size:0.85rem;">${dlHtml}</div>
          <div style="font-weight:600; color:${scoreColor}; font-size:0.95rem;">${m.match_score}% Match</div>
          <div style="font-size:0.85rem; color:var(--text-2); line-height:1.5;">
            ${m.why}
            <div style="color:var(--text-3); font-size:0.8rem; margin-top:6px;">${m.competition.description}</div>
            ${m.competition.url ? `<a href="${m.competition.url}" target="_blank" style="display:inline-block; margin-top:8px; font-size:0.8rem; color: var(--accent); font-weight: 500; text-decoration: none;">View official link →</a>` : ''}
          </div>
        </div>
      `;
    });

    html += `
      </div>
    `;
    body.innerHTML = html;
  } catch (err) {
    console.error("Error loading opportunities:", err);
    body.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load opportunities</div>';
  }
}
window.renderStudentRadar = renderStudentRadar;

// ══════════════════════════════════════════════
//  COLLEGE SHORTLIST & DEADLINE CALENDAR
// ══════════════════════════════════════════════

let studentCollegesList = [];
let studentCalendarEvents = [];

async function renderStudentShortlist() {
  const container = document.getElementById('student-colleges-list');
  if (!container) return;

  if (!createdStudentId) {
    container.innerHTML = '<div class="loading-row"><span class="blink">▌</span> submit your profile first to view college options</div>';
    return;
  }

  if (studentCollegesList.length === 0) {
    try {
      const res = await fetch('/api/colleges');
      studentCollegesList = await res.json();
    } catch (e) {
      console.error(e);
    }
  }

  filterStudentColleges();
}
window.renderStudentShortlist = renderStudentShortlist;

async function filterStudentColleges() {
  const container = document.getElementById('student-colleges-list');
  if (!container) return;

  const query = document.getElementById('student-shortlist-search').value.toLowerCase().trim();
  container.innerHTML = '';

  if (!createdStudentId) {
    container.innerHTML = '<div class="loading-row"><span class="blink">▌</span> submit your profile first to view college options</div>';
    return;
  }

  if (studentCollegesList.length === 0) {
    try {
      const res = await fetch('/api/colleges');
      studentCollegesList = await res.json();
    } catch (e) {
      console.error(e);
    }
  }

  try {
    const sRes = await fetch(`/api/students/${createdStudentId}`);
    const student = await sRes.json();
    const shortlisted = student.shortlisted_colleges || [];
    let renderCount = 0;
    for (let i = 0; i < studentCollegesList.length; i++) {
      const c = studentCollegesList[i];
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
            <strong>${dl.label}:</strong> ${dl.date} <br/>
            <span style="font-size:0.65rem; color:var(--text-3);">${dl.description}</span>
          </div>`;
      });

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
          <div>
            <h3 style="font-size:1rem; font-weight:700; color:var(--text-1);">${c.name}</h3>
            <span style="font-family:var(--mono); font-size:0.68rem; color:var(--text-3); text-transform:uppercase;">${c.country}</span>
          </div>
          <button type="button" class="${isShortlisted ? 'btn-reset' : 'btn-run'}" onclick="toggleStudentShortlist('${c.id}')" style="padding:6px 14px; font-size:0.72rem;">
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
    
    renderPinnedShortlist(student);

  } catch (err) {
    console.error(err);
    container.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load college shortlist</div>';
  }
}
window.filterStudentColleges = filterStudentColleges;

async function toggleStudentShortlist(collegeId) {
  if (!createdStudentId) return;

  try {
    const sRes = await fetch(`/api/students/${createdStudentId}`);
    const student = await sRes.json();
    let shortlisted = [...(student.shortlisted_colleges || [])];
    if (!student.shortlist_categories) student.shortlist_categories = {};
    
    if (shortlisted.includes(collegeId)) {
      shortlisted = shortlisted.filter(id => id !== collegeId);
      delete student.shortlist_categories[collegeId];
    } else {
      shortlisted.push(collegeId);
      // Fetch AI Category
      try {
        const evRes = await fetch('/api/evaluate_shortlist', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ student_id: createdStudentId, college_id: collegeId })
        });
        const evData = await evRes.json();
        student.shortlist_categories[collegeId] = evData.category || 'Target';
      } catch (e) {
        student.shortlist_categories[collegeId] = 'Target';
      }
    }

    const res = await fetch(`/api/students/${createdStudentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...student, shortlisted_colleges: shortlisted })
    });
    if (res.ok) {
      filterStudentColleges();
    } else {
      alert("Failed to update shortlist.");
    }
  } catch (err) {
    console.error(err);
  }
}

async function updateCategory(collegeId, newCat) {
  if (!createdStudentId) return;
  try {
    const sRes = await fetch(`/api/students/${createdStudentId}`);
    const student = await sRes.json();
    if (!student.shortlist_categories) student.shortlist_categories = {};
    student.shortlist_categories[collegeId] = newCat;
    
    const res = await fetch(`/api/students/${createdStudentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(student)
    });
    if (res.ok) {
      filterStudentColleges();
    }
  } catch(e) {
    console.error(e);
  }
}

function renderPinnedShortlist(student) {
  const container = document.getElementById('pinned-shortlist-container');
  if(!container) return;
  
  const shortlisted = student.shortlisted_colleges || [];
  if (shortlisted.length === 0) {
    container.innerHTML = '<span style="color: var(--text-3); font-size: 0.85rem;">You haven\'t shortlisted any colleges yet. Search and add them to see your AI predictions.</span>';
    return;
  }
  
  let html = '';
  shortlisted.forEach(cid => {
    const c = studentCollegesList.find(x => x.id === cid);
    if(!c) return;
    
    const cat = (student.shortlist_categories && student.shortlist_categories[cid]) ? student.shortlist_categories[cid] : 'Target';
    const catColors = {
      'Reach': 'var(--red)',
      'Target': 'var(--amber)',
      'Safety': 'var(--green)'
    };
    
    html += `
      <div style="background: var(--surface); border: 1px solid var(--border); padding: 12px; border-radius: 8px; display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h4 style="font-size: 0.95rem; font-weight: 600; color: var(--text-1); margin: 0;">${c.name}</h4>
          <button onclick="toggleStudentShortlist('${cid}')" style="background: none; border: none; cursor: pointer; font-size: 0.9rem; color: var(--text-3);" title="Remove">✕</button>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem;">
          <span style="color: var(--text-2);">AI Prediction:</span>
          <select onchange="updateCategory('${cid}', this.value)" style="padding: 4px; font-weight: 600; color: ${catColors[cat] || 'var(--amber)'}; background: transparent; border: 1px dashed var(--border); border-radius: 4px;">
            <option value="Reach" ${cat==='Reach'?'selected':''} style="color:var(--red);">Reach</option>
            <option value="Target" ${cat==='Target'?'selected':''} style="color:var(--amber);">Target</option>
            <option value="Safety" ${cat==='Safety'?'selected':''} style="color:var(--green);">Safety</option>
          </select>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}
window.toggleStudentShortlist = toggleStudentShortlist;

let studentCalYear = 2026;
let studentCalMonth = 6;
let studentSelectedCalDay = null;

async function renderStudentCalendar() {
  const listCont = document.getElementById('student-calendar-list');
  if (!listCont) return;

  if (!createdStudentId) {
    listCont.innerHTML = '<div class="loading-row"><span class="blink">▌</span> submit your profile first to unlock calendar</div>';
    return;
  }

  listCont.innerHTML = '<div class="loading-row"><span class="blink">▌</span> loading deadlines calendar…</div>';

  try {
    const res = await fetch(`/api/calendar/${createdStudentId}`);
    studentCalendarEvents = await res.json();
    studentSelectedCalDay = null;
    updateStudentCalendarUI();
  } catch (err) {
    console.error("Error loading calendar:", err);
    listCont.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load deadlines calendar</div>';
  }
}
window.renderStudentCalendar = renderStudentCalendar;

function navigateStudentCalendarMonth(direction) {
  studentCalMonth += direction;
  if (studentCalMonth < 0) {
    studentCalMonth = 11;
    studentCalYear -= 1;
  } else if (studentCalMonth > 11) {
    studentCalMonth = 0;
    studentCalYear += 1;
  }
  studentSelectedCalDay = null;
  updateStudentCalendarUI();
}
window.navigateStudentCalendarMonth = navigateStudentCalendarMonth;

function updateStudentCalendarUI() {
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const lbl = document.getElementById('student-calendar-month-label');
  if (lbl) {
    lbl.textContent = `${months[studentCalMonth]} ${studentCalYear}`;
  }

  renderStudentCalendarGrid();
  filterStudentCalendar();
}

function renderStudentCalendarGrid() {
  const cellsCont = document.getElementById('student-calendar-grid-cells');
  if (!cellsCont) return;
  cellsCont.innerHTML = '';

  const firstDay = new Date(studentCalYear, studentCalMonth, 1).getDay();
  const totalDays = new Date(studentCalYear, studentCalMonth + 1, 0).getDate();

  for (let i = 0; i < firstDay; i++) {
    const pad = document.createElement('div');
    pad.style.height = '42px';
    cellsCont.appendChild(pad);
  }

  const showCollege = document.getElementById('stud-cal-filter-college').checked;
  const showExam = document.getElementById('stud-cal-filter-exam').checked;
  const showComp = document.getElementById('stud-cal-filter-competition').checked;

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

    if (studentSelectedCalDay === day) {
      cell.style.borderColor = 'var(--accent)';
      cell.style.background = 'rgba(200,255,0,0.04)';
    }

    const dayLabel = document.createElement('span');
    dayLabel.textContent = day;
    dayLabel.style.color = 'var(--text-1)';
    dayLabel.style.fontWeight = '600';
    cell.appendChild(dayLabel);

    const dayEvents = studentCalendarEvents.filter(e => {
      const eDate = new Date(e.date);
      return eDate.getFullYear() === studentCalYear &&
        eDate.getMonth() === studentCalMonth &&
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
      if (studentSelectedCalDay === day) {
        studentSelectedCalDay = null;
      } else {
        studentSelectedCalDay = day;
      }
      updateStudentCalendarUI();
    };

    cellsCont.appendChild(cell);
  }
}

function filterStudentCalendar() {
  const listCont = document.getElementById('student-calendar-list');
  if (!listCont) return;
  listCont.innerHTML = '';

  const showCollege = document.getElementById('stud-cal-filter-college').checked;
  const showExam = document.getElementById('stud-cal-filter-exam').checked;
  const showComp = document.getElementById('stud-cal-filter-competition').checked;

  const currentContextDate = new Date("2026-07-25");

  const filtered = studentCalendarEvents.filter(e => {
    if (e.type === 'college' && !showCollege) return false;
    if (e.type === 'exam' && !showExam) return false;
    if (e.type === 'competition' && !showComp) return false;

    const eDate = new Date(e.date);
    const matchMonth = eDate.getFullYear() === studentCalYear && eDate.getMonth() === studentCalMonth;
    if (!matchMonth) return false;

    if (studentSelectedCalDay !== null && eDate.getDate() !== studentSelectedCalDay) return false;
    return true;
  });

  if (filtered.length === 0) {
    listCont.innerHTML = `
      <div class="loading-row" style="color:var(--text-3);">
        No events found for ${studentSelectedCalDay ? `Day ${studentSelectedCalDay}` : 'this month'} matching filters.
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
window.filterStudentCalendar = filterStudentCalendar;

// ══════════════════════════════════════════════
//  SCHOLARSHIP MONITOR
// ══════════════════════════════════════════════

async function renderStudentScholarships() {
  const body = document.getElementById('scholarships-body');
  if (!body) return;

  if (!createdStudentId) {
    body.innerHTML = '<div class="loading-row"><span class="blink">▌</span> submit your profile first to unlock scholarship recommendations</div>';
    return;
  }

  body.innerHTML = '<div class="loading-row"><span class="blink">▌</span> AI agent is evaluating your profile against available scholarships...</div>';

  try {
    const res = await fetch(`/api/match_scholarships/${createdStudentId}`);
    const matches = await res.json();

    if (!matches || matches.length === 0) {
      body.innerHTML = '<div class="loading-row">No matching scholarships found for your current profile. Try adjusting target pathways or subjects.</div>';
      return;
    }

    let html = `
      <section class="student-list" style="margin-top:20px;">
        <div class="list-header" style="grid-template-columns: 2fr 1fr 1fr 2fr; padding: 10px 20px; border-bottom: 1px solid var(--border); background: var(--surface);">
          <span class="lh-col">Scholarship</span>
          <span class="lh-col">Deadline</span>
          <span class="lh-col">Match Score</span>
          <span class="lh-col">AI Rationale (Why & Actions)</span>
        </div>
        <div class="rows-container">
    `;

    matches.forEach(m => {
      let dlHtml = '—';
      if (m.scholarship.deadline) {
        if (m.days_remaining !== null) {
          if (m.days_remaining < 0) {
            dlHtml = `<span style="color:var(--text-3);">Closed</span>`;
          } else {
            dlHtml = `<span style="color:${m.is_urgent ? 'var(--red)' : 'var(--text-2)'}; font-weight:600;">${m.scholarship.deadline}<br/><small style="font-family:var(--mono); font-size:0.6rem;">(${m.days_remaining} days left)</small></span>`;
          }
        } else {
          dlHtml = `<span>${m.scholarship.deadline}</span>`;
        }
      }

      const scoreColor = m.match_score >= 80 ? 'var(--green)' : m.match_score >= 50 ? 'var(--amber)' : 'var(--red)';

      html += `
        <div class="stu-row" style="grid-template-columns: 2fr 1fr 1fr 2fr; cursor: default;">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <strong style="font-size:0.85rem; color:var(--text-1);">${m.scholarship.name}</strong>
            <span style="font-size:0.68rem; color:var(--text-3); font-family:var(--mono);">${m.scholarship.type} · ${m.scholarship.provider}</span>
            <span style="font-size:0.65rem; color:var(--amber); font-weight:600; margin-top:2px;">Award: ${m.scholarship.award_value}</span>
          </div>
          <div style="font-size:0.75rem;">${dlHtml}</div>
          <div style="font-family:var(--mono); font-weight:700; color:${scoreColor}; font-size:0.85rem;">${m.match_score}% Match</div>
          <div style="font-size:0.72rem; color:var(--text-2); line-height:1.4;">
            <div style="margin-bottom:6px;"><strong style="color:var(--text-1);">Why:</strong><ul style="margin:4px 0 0 16px;">${m.why.split('\\n').map(line => `<li>${line}</li>`).join('')}</ul></div>
            <div style="color:var(--amber);"><strong style="color:var(--amber);">Actions needed:</strong><ul style="margin:4px 0 0 16px;">${m.actions_needed.split('\\n').map(line => `<li>${line}</li>`).join('')}</ul></div>
            ${m.scholarship.url ? `<a href="${m.scholarship.url}" target="_blank" class="student-link" style="display:inline-block; margin-top:6px; font-size:0.68rem; font-family:var(--mono);">visit official link ↗</a>` : ''}
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </section>
    `;
    body.innerHTML = html;
  } catch (err) {
    console.error("Error loading scholarships:", err);
    body.innerHTML = '<div class="loading-row" style="color:var(--red);">✕ failed to load scholarships</div>';
  }
}
window.renderStudentScholarships = renderStudentScholarships;

// ══════════════════════════════════════════════
//  STUDENT APPLICATION RECYCLING (ALUMNI PATHWAYS)
// ══════════════════════════════════════════════

async function renderStudentRecyclingView() {
  const grid = document.getElementById('student-alumni-grid');
  const emptyState = document.getElementById('student-alumni-empty');
  if (!grid) return;

  grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-3);">Loading alumni pathways...</div>';
  emptyState.classList.add('hidden');

  try {
    const res = await fetch('/api/alumni');
    const alumni = await res.json();

    const searchQ = (document.getElementById('student-alumni-search')?.value || '').toLowerCase();
    const filtered = alumni.filter(a => 
      a.name.toLowerCase().includes(searchQ) || 
      (a.admitted_to || []).some(u => u.toLowerCase().includes(searchQ)) ||
      (a.board || '').toLowerCase().includes(searchQ)
    );

    if (filtered.length === 0) {
      grid.innerHTML = '';
      emptyState.classList.remove('hidden');
      return;
    }

    grid.innerHTML = filtered.map(a => `
      <div class="form-card" style="display:flex; flex-direction:column; gap:16px; transition:transform 0.2s;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
          <div>
            <h4 style="margin:0; font-size:1.1rem; color:var(--text-1);">${a.name}</h4>
            <div style="font-size:0.8rem; color:var(--text-3);">${a.board || 'N/A'} • ${a.graduating_class || 'N/A'}</div>
          </div>
          <div style="background:var(--success-bg); color:var(--success-text); padding:4px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">
            Admitted
          </div>
        </div>
        
        <div>
          <div style="font-size:0.85rem; font-weight:600; color:var(--text-2); margin-bottom:4px;">Admitted To:</div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            ${(a.admitted_to || []).map(u => `<span class="badge match">${u}</span>`).join('')}
          </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
          <div style="background:var(--bg); padding:10px; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-3);">Academics</div>
            <div style="font-size:0.9rem; font-weight:600; color:var(--text-1);">${a.grades?.final_score || a.grades?.expected_score || 'N/A'}</div>
          </div>
          <div style="background:var(--bg); padding:10px; border-radius:8px;">
            <div style="font-size:0.75rem; color:var(--text-3);">Testing</div>
            <div style="font-size:0.9rem; font-weight:600; color:var(--text-1);">${Object.entries(a.standardized_tests || {}).map(([k,v])=>k+': '+v).join(', ') || 'Test Optional'}</div>
          </div>
        </div>

        <div style="border-top:1px solid var(--border); padding-top:12px; margin-top:auto;">
          <div style="font-size:0.85rem; font-weight:600; color:var(--text-2); margin-bottom:8px;">🎓 Proven Pathway:</div>
          <div style="font-size:0.85rem; color:var(--text-1); line-height:1.4; margin-bottom:12px;">
            ${a.key_remediation_taken || 'Standard application pathway.'}
          </div>
          <button class="btn btn-secondary" style="width:100%; justify-content:center;" onclick="openConnectionModal('${a.id}', '${a.name.replace(/'/g, "\\'")}')">
            Connect for Advice
          </button>
        </div>
      </div>
    `).join('');

  } catch (err) {
    console.error(err);
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:red;">Failed to load alumni data.</div>';
  }
  
  await renderStudentConnections();
}

async function renderStudentConnections() {
  const listCont = document.getElementById('student-connections-list');
  const emptyState = document.getElementById('student-connections-empty');
  if (!listCont) return;

  try {
    const res = await fetch('/api/connections/student');
    if (!res.ok) throw new Error('Failed to fetch connections');
    const connections = await res.json();
    
    if (connections.length === 0) {
      listCont.innerHTML = '';
      emptyState.style.display = 'block';
      return;
    }
    
    emptyState.style.display = 'none';
    
    // Sort descending by date
    connections.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    listCont.innerHTML = connections.map(c => {
      let statusBadge = '';
      if (c.status === 'pending') statusBadge = '<span class="badge missing">Pending Review</span>';
      else if (c.status === 'approved') statusBadge = '<span class="badge match">Approved & Forwarded</span>';
      else if (c.status === 'rejected') statusBadge = '<span class="badge partial">Rejected</span>';
      
      const dateStr = new Date(c.created_at).toLocaleDateString();
      
      return `
        <div style="background:var(--bg); border:1px solid var(--border); border-radius:12px; padding:16px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
              <h4 style="margin:0; font-size:1.05rem; color:var(--text-1);">Request to Alumni: ${c.alumni_id}</h4>
              <div style="font-size:0.8rem; color:var(--text-3); margin-top:4px;">Requested on ${dateStr}</div>
            </div>
            <div>${statusBadge}</div>
          </div>
          <div style="background:var(--surface); padding:12px; border-radius:8px; font-size:0.9rem; color:var(--text-2); white-space:pre-wrap;">${c.message}</div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
    listCont.innerHTML = '<div style="color:red; text-align:center;">Failed to load your connections.</div>';
  }
}
window.renderStudentRecyclingView = renderStudentRecyclingView;


window.nextWizardStep = function(stepNum) {
  document.querySelectorAll('.wizard-sec').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.wizard-sec').forEach(el => el.style.display = 'none');
  
  const sec = document.getElementById('wizard-sec-' + stepNum);
  if (sec) {
    sec.classList.remove('hidden');
    sec.style.display = 'block';
  }
  
  document.querySelectorAll('.wizard-step').forEach(el => {
    el.classList.remove('active');
    el.style.fontWeight = 'normal';
    el.style.color = 'var(--text-3)';
  });
  const stepLabel = document.getElementById('wstep-' + stepNum);
  if (stepLabel) {
    stepLabel.classList.add('active');
    stepLabel.style.fontWeight = 'bold';
    stepLabel.style.color = 'var(--accent)';
  }
};

window.lockTabs = function() {
  const tabs = ['results', 'radar', 'shortlist', 'calendar', 'scholarships', 'recycling'];
  tabs.forEach(t => {
    const el = document.getElementById('tab-' + t);
    if(el) {
      el.style.opacity = '0.5';
      el.style.pointerEvents = 'none';
    }
  });
};

window.unlockTabs = function() {
  const tabs = ['results', 'radar', 'shortlist', 'calendar', 'scholarships', 'recycling'];
  tabs.forEach(t => {
    const el = document.getElementById('tab-' + t);
    if(el) {
      el.style.opacity = '1';
      el.style.pointerEvents = 'auto';
    }
  });
};
window.openConnectionModal = function(alumniId, alumniName) {
  document.getElementById('conn-alumni-id').value = alumniId;
  document.getElementById('conn-alumni-name').textContent = alumniName;
  document.getElementById('conn-message').value = '';
  document.getElementById('connection-modal').classList.remove('hidden');
  document.getElementById('connection-modal').style.display = 'flex';
};

window.submitConnectionRequest = async function() {
  const alumniId = document.getElementById('conn-alumni-id').value;
  const message = document.getElementById('conn-message').value.trim();
  
  if (!message) {
    alert('Please enter a message to the alumni.');
    return;
  }
  
  const btn = document.querySelector('#connection-modal .btn-primary');
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Sending...';
  
  try {
    const res = await fetch('/api/connections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        alumni_id: alumniId,
        student_id: currentUserStudentId || 'student',
        message: message
      })
    });
    
    if (res.ok) {
      alert('Your request has been submitted for counselor review.');
      document.getElementById('connection-modal').style.display = 'none';
      document.getElementById('connection-modal').classList.add('hidden');
      await renderStudentConnections();
    } else {
      const err = await res.json();
      alert('Failed to send request: ' + (err.error || 'Unknown error'));
    }
  } catch (err) {
    console.error(err);
    alert('Network error when submitting request.');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
};
