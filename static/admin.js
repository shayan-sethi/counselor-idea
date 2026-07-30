let allUsers = [];
let targetUsername = null;
let pendingBulkStudents = [];

function switchView(viewId) {
  // Update Nav
  document.getElementById('tab-users').classList.toggle('active', viewId === 'users');
  document.getElementById('tab-ingestion').classList.toggle('active', viewId === 'ingestion');

  // Update Main views
  document.getElementById('view-users').classList.toggle('hidden', viewId !== 'users');
  document.getElementById('view-ingestion').classList.toggle('hidden', viewId !== 'ingestion');
}

async function loadUsers() {
  const tbody = document.getElementById('user-table-body');
  try {
    const res = await fetch('/api/admin/users');
    if (!res.ok) throw new Error('Failed to load users');
    allUsers = await res.json();
    
    tbody.innerHTML = '';
    if (allUsers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No users found</td></tr>';
      return;
    }

    allUsers.forEach(u => {
      const badgeClass = `badge-${u.role}`;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight: 600;">${u.username}</td>
        <td><span class="${badgeClass}">${u.role.toUpperCase()}</span></td>
        <td>${u.student_id || '<span style="color: var(--text-3);">—</span>'}</td>
        <td>
          <button class="btn-secondary" onclick="openResetModal('${u.username}')">Reset Password</button>
          <button class="btn-danger" style="margin-left: 8px;" onclick="deleteUser('${u.username}')">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch(err) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: red;">${err.message}</td></tr>`;
  }
}

function toggleStudentId() {
  const role = document.getElementById('add-role').value;
  document.getElementById('student-id-group').style.display = role === 'student' ? 'block' : 'none';
}

function openAddModal() {
  document.getElementById('add-username').value = '';
  document.getElementById('add-password').value = '';
  document.getElementById('add-role').value = 'student';
  document.getElementById('add-studentid').value = '';
  toggleStudentId();
  document.getElementById('add-modal').style.display = 'flex';
}

function openResetModal(username) {
  targetUsername = username;
  document.getElementById('reset-target-user').textContent = username;
  document.getElementById('reset-password').value = '';
  document.getElementById('reset-modal').style.display = 'flex';
}

function closeModals() {
  document.getElementById('add-modal').style.display = 'none';
  document.getElementById('reset-modal').style.display = 'none';
  targetUsername = null;
}

async function submitAddUser() {
  const username = document.getElementById('add-username').value.trim();
  const password = document.getElementById('add-password').value;
  const role = document.getElementById('add-role').value;
  let student_id = document.getElementById('add-studentid').value.trim();
  if (role !== 'student') student_id = null;

  if (!username || !password) { alert('Username and password are required'); return; }

  try {
    const res = await fetch('/api/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role, student_id })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to create user');
    alert('User created successfully');
    closeModals();
    loadUsers();
  } catch(err) {
    alert(err.message);
  }
}

async function submitResetPassword() {
  const password = document.getElementById('reset-password').value;
  if (!password) { alert('Password is required'); return; }

  try {
    const res = await fetch(`/api/admin/users/${targetUsername}/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to reset password');
    alert('Password updated successfully');
    closeModals();
  } catch(err) {
    alert(err.message);
  }
}

async function deleteUser(username) {
  if (!confirm(`Are you sure you want to delete the user "${username}"? This cannot be undone.`)) return;

  try {
    const res = await fetch(`/api/admin/users/${username}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to delete user');
    loadUsers();
  } catch(err) {
    alert(err.message);
  }
}

window.handleBulkIngestFile = async function(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const statusEl = document.getElementById('admin-ingest-status');
  statusEl.style.display = 'block';
  statusEl.innerHTML = '<span class="blink">▌</span> Uploading and mapping CSV via AI...';
  
  const formData = new FormData();
  formData.append("file", file);
  
  try {
    const res = await fetch("/api/bulk_ingest_preview", {
      method: "POST",
      body: formData
    });
    
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Failed to parse spreadsheet");
    
    pendingBulkStudents = data.previews;
    
    document.getElementById('modal-bulk-ingest').style.display = 'flex';
    document.getElementById('bulk-ingest-status').innerHTML = `✔ AI mapped columns successfully! Found ${data.previews.length} students.`;
    
    const tbody = document.getElementById('bulk-ingest-table-body');
    tbody.innerHTML = '';
    
    data.previews.forEach(s => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid var(--border)';
      tr.innerHTML = `
        <td style="padding:8px;">${s.name || '-'}</td>
        <td style="padding:8px;">${s.class_level || '-'}</td>
        <td style="padding:8px;">${s.board || '-'}</td>
        <td style="padding:8px; font-size:0.75rem;">${(s.board_subjects || []).join(', ')}</td>
        <td style="padding:8px; font-size:0.75rem;">${(s.targets || []).join(', ')}</td>
      `;
      tbody.appendChild(tr);
    });
    
  } catch (err) {
    statusEl.innerHTML = `<span style="color:var(--red);">Error: ${err.message}</span>`;
  }
  
  event.target.value = "";
}

window.confirmBulkIngest = async function() {
  const btn = document.getElementById('btn-confirm-bulk');
  btn.innerHTML = 'Importing...';
  btn.disabled = true;
  
  try {
    const res = await fetch("/api/bulk_ingest_save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ students: pendingBulkStudents })
    });
    
    if (!res.ok) throw new Error("Failed to save");
    
    document.getElementById('modal-bulk-ingest').style.display = 'none';
    const statusEl = document.getElementById('admin-ingest-status');
    statusEl.innerHTML = `✔ Successfully imported ${pendingBulkStudents.length} students!`;
    setTimeout(() => { statusEl.style.display = 'none'; }, 5000);
    
    // Automatically switch to user management and reload users to show the new STU_ accounts
    switchView('users');
    loadUsers();
  } catch (err) {
    alert("Error saving: " + err.message);
  } finally {
    btn.innerHTML = 'Confirm & Import Students';
    btn.disabled = false;
  }
}

// Init
window.onload = async () => {
  const authed = await checkUserSession();
  if (!authed) return;
  if (currentUserRole !== 'admin') {
    window.location.href = '/static/login.html';
    return;
  }
  loadUsers();
};
