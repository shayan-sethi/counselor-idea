import re

with open('static/student.html', 'r') as f:
    html = f.read()

# Replace tab-profile text and id with Dashboard
html = html.replace('id="tab-profile" onclick="showStep(\'profile\')">Your Profile</button>', 'id="tab-dash" onclick="showStep(\'dash\')">Dashboard</button>')
html = html.replace('id="tab-results" onclick="showStep(\'results\')">Audit Results</button>', 'id="tab-results" onclick="showStep(\'results\')">Audit Results</button>\n      <button class="nav-item" id="tab-onboarding" style="display:none;" onclick="showStep(\'onboarding\')">Setup Profile</button>')

# The main section for step-profile
# Let's replace the whole main block. We'll find it using regex or string splitting
start_tag = '<!-- ═══ PROFILE FORM ═══ -->'
end_tag = '<!-- ═══ RESULTS ═══ -->'
start_idx = html.find(start_tag)
end_idx = html.find(end_tag)

onboarding_html = """<!-- ═══ ONBOARDING WIZARD ═══ -->
  <main id="step-onboarding">
    <div class="dash-header">
      <div>
        <div class="greeting">Welcome to unlockED</div>
        <div class="greeting-sub">Let's set up your profile to unlock your personalized pathway.</div>
      </div>
    </div>
    <div class="wizard-container" style="max-width: 700px; margin: 0 auto; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
      
      <!-- Progress Bar -->
      <div style="display:flex; justify-content: space-between; margin-bottom: 24px;">
        <div class="wizard-step active" id="wstep-1">1. Basics</div>
        <div class="wizard-step" id="wstep-2">2. Grades</div>
        <div class="wizard-step" id="wstep-3">3. Extracurriculars</div>
      </div>
      
      <form id="student-wizard-form" onsubmit="submitWizard(event)">
        <!-- Step 1 -->
        <div id="wizard-sec-1" class="wizard-sec">
          <h2 style="font-size: 1.2rem; color: var(--text-1); margin-bottom: 16px;">Basic Information</h2>
          <div class="form-row" style="margin-bottom: 16px;">
            <div class="field field-wide">
              <label>Your Full Name *</label>
              <input type="text" id="sf-name" required placeholder="e.g. Aarav Sharma" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;" />
            </div>
          </div>
          <div class="form-row" style="margin-bottom: 16px; display:flex; gap:16px;">
            <div class="field" style="flex:1;">
              <label>Board *</label>
              <select id="sf-board" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;">
                <option value="CBSE">CBSE</option>
                <option value="ICSE">ICSE</option>
                <option value="State Board">State Board</option>
                <option value="IB">IB</option>
                <option value="A-Levels">A-Levels</option>
              </select>
            </div>
            <div class="field" style="flex:1;">
              <label>Class Level *</label>
              <select id="sf-class" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;">
                <option value="10">Class 10</option>
                <option value="11">Class 11</option>
                <option value="12" selected>Class 12</option>
              </select>
            </div>
          </div>
          <div class="field" style="margin-bottom: 16px;">
            <label>Select Your Subjects</label>
            <div class="check-grid" id="sf-subjects" style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;"></div>
          </div>
          <button type="button" class="btn-primary" onclick="nextWizardStep(2)" style="width:100%; padding:12px; border-radius:8px;">Next Step →</button>
        </div>

        <!-- Step 2 -->
        <div id="wizard-sec-2" class="wizard-sec hidden" style="display:none;">
          <h2 style="font-size: 1.2rem; color: var(--text-1); margin-bottom: 16px;">Grades & Test Scores</h2>
          <div class="form-row" style="display:flex; gap:16px; margin-bottom: 16px;">
            <div class="field" style="flex:1;">
              <label>Grade 10 Aggregate</label>
              <input type="text" id="sf-g10" placeholder="e.g. 88%" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;" />
            </div>
            <div class="field" style="flex:1;">
              <label>Class 11/12 Expected</label>
              <input type="text" id="sf-gexp" placeholder="e.g. 90%" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;" />
            </div>
          </div>
          <div class="form-row" style="display:flex; gap:16px; margin-bottom: 16px;">
            <div class="field" style="flex:1;">
              <label>SAT Score (if any)</label>
              <input type="number" id="sf-sat" placeholder="e.g. 1480" style="width:100%; padding:10px; background:rgba(0,0,0,0.2); border:1px solid var(--border); color:var(--text-1); border-radius:8px;" />
            </div>
          </div>
          <div style="display:flex; gap:12px;">
            <button type="button" class="btn-outline" onclick="nextWizardStep(1)" style="flex:1; padding:12px; border-radius:8px;">← Back</button>
            <button type="button" class="btn-primary" onclick="nextWizardStep(3)" style="flex:1; padding:12px; border-radius:8px;">Next Step →</button>
          </div>
        </div>

        <!-- Step 3 -->
        <div id="wizard-sec-3" class="wizard-sec hidden" style="display:none;">
          <h2 style="font-size: 1.2rem; color: var(--text-1); margin-bottom: 16px;">Extracurriculars</h2>
          <p style="font-size: 0.85rem; color: var(--text-2); margin-bottom: 16px;">List your top activities. Our AI will assess the impact level automatically.</p>
          <div id="sf-portfolio-list" style="margin-bottom: 16px;"></div>
          <button type="button" class="btn-outline" onclick="addStudentPortfolioRow()" style="width:100%; padding:10px; border-radius:8px; margin-bottom:16px;">+ Add Activity</button>
          <div style="display:flex; gap:12px;">
            <button type="button" class="btn-outline" onclick="nextWizardStep(2)" style="flex:1; padding:12px; border-radius:8px;">← Back</button>
            <button type="submit" class="btn-primary" style="flex:1; padding:12px; border-radius:8px; background:linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border:none; color:white;">Submit Profile →</button>
          </div>
        </div>
      </form>
    </div>
  </main>
  
  <!-- ═══ DASHBOARD ═══ -->
  <main id="step-dash" class="hidden" style="display:none;">
    <div class="dash-header">
      <div>
        <div class="greeting">Student Dashboard</div>
        <div class="greeting-sub">Your AI-powered admission pathway</div>
      </div>
      <div>
        <button class="btn-primary" onclick="showStep('onboarding')">Edit Profile</button>
      </div>
    </div>
    
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon" style="background:#E0E7FF; color:#4F46E5;">
             <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
          </div>
        </div>
        <div class="kpi-value" id="dash-grade-value">—</div>
        <div class="kpi-label">Expected Grades</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon" style="background:#D1FAE5; color:#059669;">
             <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          </div>
        </div>
        <div class="kpi-value" id="dash-sat-value">—</div>
        <div class="kpi-label">Test Scores</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-top">
          <div class="kpi-icon" style="background:#FEF3C7; color:#D97706;">
             <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
        </div>
        <div class="kpi-value" id="dash-activities-value">—</div>
        <div class="kpi-label">Activities Logged</div>
      </div>
    </div>
    
    <div style="margin-top: 24px; padding: 24px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px;">
      <h2 style="font-size: 1.2rem; margin-bottom: 16px; color: var(--text-1);">Welcome to your dashboard</h2>
      <p style="color: var(--text-2); font-size: 0.95rem; line-height: 1.6;">
        Explore the tabs on the left to view your compliance audit, find scholarships, map your application deadlines, and view opportunities tailored to your profile.
      </p>
      <button class="btn-primary" style="margin-top: 16px;" onclick="showStep('results')">View Audit Results</button>
    </div>
  </main>
"""

new_html = html[:start_idx] + onboarding_html + "\n  " + html[end_idx:]

with open('static/student.html', 'w') as f:
    f.write(new_html)

