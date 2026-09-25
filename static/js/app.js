// Current Application State
let currentUser = null;
let currentView = 'dashboard';

// On Page Load
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthStatus();
  if (currentUser) {
    setupViewForRole();
    loadDashboardData();
  }
});

// ================= AUTHENTICATION LOGIC (NO OTP) =================

function switchAuthTab(tab) {
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const tabLogin = document.getElementById('tab-login');
  const tabSignup = document.getElementById('tab-signup');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
    tabLogin.classList.add('active');
    tabSignup.classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    signupForm.classList.remove('hidden');
    tabLogin.classList.remove('active');
    tabSignup.classList.add('active');
  }
}

function fillDemo(username, password) {
  document.getElementById('login-username').value = username;
  document.getElementById('login-password').value = password;
}

function updateRoleBadge(role) {
  // Handled dynamically on form submission
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Login failed');

    currentUser = data.user;
    showToast(`Welcome back, ${currentUser.name}!`, 'success');
    showAppScreen();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const name = document.getElementById('signup-name').value.trim();
  const mobile_no = document.getElementById('signup-mobile').value.trim();
  const username = document.getElementById('signup-username').value.trim();
  const password = document.getElementById('signup-password').value.trim();
  const role = document.querySelector('input[name="signup-role"]:checked').value;

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, mobile_no, username, password, role })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Registration failed');

    currentUser = data.user;
    showToast(`Account created as ${role.toUpperCase()}!`, 'success');
    showAppScreen();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function checkAuthStatus() {
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json();
    if (data.authenticated) {
      currentUser = data.user;
      showAppScreen();
    } else {
      showAuthScreen();
    }
  } catch (err) {
    showAuthScreen();
  }
}

async function handleLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  currentUser = null;
  showToast('Logged out successfully', 'info');
  showAuthScreen();
}

function showAuthScreen() {
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app-screen').classList.add('hidden');
}

function showAppScreen() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app-screen').classList.remove('hidden');

  document.getElementById('display-user-name').textContent = currentUser.name || currentUser.username;
  document.getElementById('display-user-handle').textContent = `@${currentUser.username}`;
  
  const initials = (currentUser.name || currentUser.username).slice(0, 2).toUpperCase();
  document.getElementById('user-avatar-initials').textContent = initials;

  const roleBadge = document.getElementById('user-role-badge');
  roleBadge.textContent = currentUser.role.toUpperCase();
  if (currentUser.role === 'patient') {
    roleBadge.classList.add('role-patient');
  } else {
    roleBadge.classList.remove('role-patient');
  }

  setupViewForRole();
  switchView('dashboard');
}

function setupViewForRole() {
  const isStaff = currentUser && currentUser.role === 'staff';
  
  document.querySelectorAll('.staff-only').forEach(el => {
    if (isStaff) {
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  });

  const patientNavText = document.getElementById('nav-patients-text');
  if (patientNavText) {
    patientNavText.textContent = isStaff ? 'All Patients' : 'My Health Profile';
  }

  const quickActionText = document.getElementById('quick-action-text');
  if (quickActionText) {
    quickActionText.textContent = isStaff ? 'New Record' : 'Book Appointment';
  }
}

// ================= VIEW SWITCHING =================

function switchView(viewName) {
  currentView = viewName;
  
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.classList.remove('active');
  });
  
  const currentNavBtn = Array.from(document.querySelectorAll('.sidebar-nav .nav-item'))
    .find(b => b.getAttribute('onclick')?.includes(viewName));
  if (currentNavBtn) currentNavBtn.classList.add('active');

  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) targetView.classList.add('active');

  const titleMap = {
    dashboard: ['Hospital Overview', 'Real-time clinical metrics & status'],
    employees: ['Medical Doctors & Staff', 'Registered clinical practitioners'],
    patients: [currentUser.role === 'staff' ? 'Patient Database' : 'My Medical Profile', 'Patient records and billing details'],
    consultations: ['Consultation Appointments', 'Scheduled doctor consultations'],
    prescriptions: ['Digital Prescriptions', 'Medical diagnoses and prescribed drugs'],
    pharmacy: ['Pharmacy Inventory', 'Medicine stocks and current rates'],
    emt: ['Emergency Ambulance Fleet', 'Live EMT vehicles readiness']
  };

  if (titleMap[viewName]) {
    document.getElementById('page-title').textContent = titleMap[viewName][0];
    document.getElementById('page-subtitle').textContent = titleMap[viewName][1];
  }

  if (viewName === 'dashboard') loadDashboardData();
  if (viewName === 'employees') loadEmployees();
  if (viewName === 'patients') loadPatients();
  if (viewName === 'consultations') loadConsultations();
  if (viewName === 'prescriptions') loadPrescriptions();
  if (viewName === 'pharmacy') loadPharmacy();
  if (viewName === 'emt') loadEmt();
}

function openNewActionModal() {
  if (currentUser.role === 'patient') {
    openModal('modal-add-consultation');
  } else {
    openModal('modal-add-patient');
  }
}

// ================= DATA LOADERS =================

async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard/stats');
    const stats = await res.json();

    document.getElementById('stat-consultations').textContent = stats.scheduled_consultations || 0;
    document.getElementById('stat-patients').textContent = stats.patients || 0;
    document.getElementById('stat-employees').textContent = stats.employees || 0;
    document.getElementById('stat-ambulances').textContent = stats.available_ambulances || 0;

    const conRes = await fetch('/api/consultations');
    const consultations = await conRes.json();
    const dashConTbody = document.getElementById('dash-consultations-tbody');
    dashConTbody.innerHTML = consultations.slice(0, 4).map(c => `
      <tr>
        <td><strong>${escapeHtml(c.PATIENT_NAME)}</strong></td>
        <td>${escapeHtml(c.DOCTOR_NAME)}</td>
        <td>${escapeHtml(c.REASON)}</td>
        <td><span class="status-pill status-${c.STATUS.toLowerCase()}">${c.STATUS}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="4" class="text-muted">No appointments found.</td></tr>';

    const emtRes = await fetch('/api/emt');
    const emts = await emtRes.json();
    const dashEmtTbody = document.getElementById('dash-emt-tbody');
    dashEmtTbody.innerHTML = emts.slice(0, 4).map(e => `
      <tr>
        <td><strong>${escapeHtml(e.VNO)}</strong></td>
        <td>${escapeHtml(e.VTYPE)}</td>
        <td>${escapeHtml(e.DRIVER_NAME)}</td>
        <td><span class="status-pill status-${e.STATUS.toLowerCase()}">${e.STATUS}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="4">No ambulances found.</td></tr>';
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
  }
}

async function loadEmployees() {
  try {
    const res = await fetch('/api/employees');
    const list = await res.json();
    const tbody = document.getElementById('employees-tbody');
    tbody.innerHTML = list.map(emp => `
      <tr>
        <td><code>${escapeHtml(emp.EID)}</code></td>
        <td><strong>${escapeHtml(emp.NAME)}</strong></td>
        <td><span class="badge-role">${escapeHtml(emp.DEPARTMENT)}</span></td>
        <td>${emp.AGE} yrs / ${escapeHtml(emp.GENDER)}</td>
        <td>₹${emp.SALARY.toLocaleString()}</td>
        <td>${escapeHtml(emp.MOBILE_NO || 'N/A')}</td>
        <td>
          <button class="btn-danger-sm" onclick="deleteEmployee('${emp.EID}')">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="7">No employees found.</td></tr>';
  } catch (err) {
    showToast('Failed to load employees', 'error');
  }
}

async function loadPatients() {
  try {
    const res = await fetch('/api/patients');
    const list = await res.json();
    const tbody = document.getElementById('patients-tbody');
    const isStaff = currentUser.role === 'staff';

    tbody.innerHTML = list.map(pat => `
      <tr>
        <td><code>${escapeHtml(pat.PID)}</code></td>
        <td><strong>${escapeHtml(pat.NAME)}</strong></td>
        <td>${escapeHtml(pat.ISSUE || 'General')}</td>
        <td>${pat.AGE || '--'} / ${escapeHtml(pat.GENDER || '--')}</td>
        <td>₹${(pat.FEES || 0).toLocaleString()}</td>
        <td>${escapeHtml(pat.MOBILE_NO || 'N/A')}</td>
        <td><span class="badge-role">${escapeHtml(pat.BILL_NO || 'N/A')}</span></td>
        ${isStaff ? `<td><button class="btn-danger-sm" onclick="deletePatient('${pat.PID}')"><i class="fa-solid fa-trash"></i></button></td>` : ''}
      </tr>
    `).join('') || '<tr><td colspan="8">No patient records available.</td></tr>';
  } catch (err) {
    showToast('Failed to load patient records', 'error');
  }
}

async function loadConsultations() {
  try {
    const res = await fetch('/api/consultations');
    const list = await res.json();
    const tbody = document.getElementById('consultations-tbody');
    const isStaff = currentUser.role === 'staff';

    tbody.innerHTML = list.map(c => `
      <tr>
        <td><code>${escapeHtml(c.CONSULTATION_ID)}</code></td>
        <td><strong>${escapeHtml(c.PATIENT_NAME)}</strong></td>
        <td>${escapeHtml(c.DOCTOR_NAME)} <small>(${escapeHtml(c.DEPARTMENT)})</small></td>
        <td>${escapeHtml(c.REASON)}</td>
        <td>₹${(c.FEES || 0).toLocaleString()}</td>
        <td>${escapeHtml(c.TIME)}</td>
        <td><span class="status-pill status-${c.STATUS.toLowerCase()}">${c.STATUS}</span></td>
        ${isStaff ? `
          <td>
            ${c.STATUS === 'Scheduled' ? `<button class="btn btn-sm btn-primary" onclick="preparePrescriptionFor('${c.CONSULTATION_ID}')"><i class="fa-solid fa-prescription"></i> Prescribe</button>` : '<small class="text-muted">Completed</small>'}
          </td>
        ` : ''}
      </tr>
    `).join('') || '<tr><td colspan="8">No consultations scheduled.</td></tr>';
  } catch (err) {
    showToast('Failed to load consultations', 'error');
  }
}

async function loadPrescriptions() {
  try {
    const res = await fetch('/api/prescriptions');
    const list = await res.json();
    const container = document.getElementById('prescriptions-container');

    container.innerHTML = list.map(rx => `
      <div class="prescription-card">
        <div class="rx-head">
          <span class="rx-num"><i class="fa-solid fa-file-waveform"></i> ${escapeHtml(rx.PRESCRIPTION_ID)}</span>
          <span class="rx-date">${escapeHtml(rx.DATE)}</span>
        </div>
        <div class="rx-patient">${escapeHtml(rx.PATIENT_NAME)}</div>
        <small class="text-muted"><i class="fa-solid fa-user-doctor"></i> Prescribed by ${escapeHtml(rx.DOCTOR_NAME)}</small>
        <div class="rx-diag"><strong>Diagnosis:</strong> ${escapeHtml(rx.DIAGNOSIS)}</div>
        ${rx.INSTRUCTIONS ? `<div class="rx-diag"><strong>Instructions:</strong> ${escapeHtml(rx.INSTRUCTIONS)}</div>` : ''}
        <div class="rx-meds-list">
          ${rx.medicines.map(m => `
            <div class="rx-med-item">
              <span><strong>${escapeHtml(m.MEDICINE_NAME)}</strong> (${escapeHtml(m.DOSAGE)})</span>
              <span>${escapeHtml(m.FREQUENCY)} - ${escapeHtml(m.DURATION)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('') || '<p class="text-muted">No prescriptions recorded yet.</p>';
  } catch (err) {
    showToast('Failed to load prescriptions', 'error');
  }
}

async function loadPharmacy() {
  try {
    const res = await fetch('/api/pharmacy');
    const list = await res.json();
    const tbody = document.getElementById('pharmacy-tbody');
    const isStaff = currentUser.role === 'staff';

    tbody.innerHTML = list.map(med => `
      <tr>
        <td><strong>${escapeHtml(med.MEDICINE_NAME)}</strong></td>
        <td><span class="badge-role">${escapeHtml(med.MEDICINE_TYPE)}</span></td>
        <td>
          <span style="color: ${med.STOCK < 50 ? '#f87171' : '#34d399'}; font-weight: 700;">
            ${med.STOCK} units ${med.STOCK < 50 ? '(Low)' : ''}
          </span>
        </td>
        <td>₹${med.PRICE.toFixed(2)}</td>
        ${isStaff ? `
          <td>
            <button class="btn btn-sm btn-outline" onclick="promptRestock('${escapeHtml(med.MEDICINE_NAME)}', ${med.STOCK})">
              <i class="fa-solid fa-boxes-stacked"></i> Update Stock
            </button>
          </td>
        ` : ''}
      </tr>
    `).join('') || '<tr><td colspan="5">Pharmacy inventory is empty.</td></tr>';
  } catch (err) {
    showToast('Failed to load pharmacy stock', 'error');
  }
}

async function loadEmt() {
  try {
    const res = await fetch('/api/emt');
    const list = await res.json();
    const tbody = document.getElementById('emt-tbody');
    const isStaff = currentUser.role === 'staff';

    tbody.innerHTML = list.map(e => `
      <tr>
        <td><code>${escapeHtml(e.VNO)}</code></td>
        <td><strong>${escapeHtml(e.VTYPE)}</strong></td>
        <td>${escapeHtml(e.DRIVER_NAME)}</td>
        <td><a href="tel:${e.MOBILE_NO}" style="color: #38bdf8; text-decoration: none;"><i class="fa-solid fa-phone"></i> ${escapeHtml(e.MOBILE_NO)}</a></td>
        <td><span class="status-pill status-${e.STATUS.toLowerCase()}">${e.STATUS}</span></td>
        ${isStaff ? `
          <td>
            <select onchange="updateEmtStatus('${e.VNO}', this.value)" style="padding: 4px 8px; border-radius: 6px; background: rgba(0,0,0,0.5); color: #fff; border: 1px solid var(--border-color);">
              <option value="Available" ${e.STATUS === 'Available' ? 'selected' : ''}>Available</option>
              <option value="Dispatched" ${e.STATUS === 'Dispatched' ? 'selected' : ''}>Dispatched</option>
              <option value="Maintenance" ${e.STATUS === 'Maintenance' ? 'selected' : ''}>Maintenance</option>
            </select>
          </td>
        ` : ''}
      </tr>
    `).join('') || '<tr><td colspan="6">No ambulances found.</td></tr>';
  } catch (err) {
    showToast('Failed to load EMT fleet', 'error');
  }
}

// ================= MODAL & MUTATION HANDLERS =================

function openModal(modalId) {
  if (modalId === 'modal-add-consultation') {
    populateConsultationDropdowns();
  }
  if (modalId === 'modal-add-prescription') {
    populatePrescriptionDropdowns();
    const medsCont = document.getElementById('rx-meds-container');
    if (medsCont) medsCont.innerHTML = '';
    addMedicineRow();
  }
  document.getElementById(modalId)?.classList.remove('hidden');
}

function closeModal(modalId) {
  document.getElementById(modalId)?.classList.add('hidden');
}

async function populateConsultationDropdowns() {
  const patSelect = document.getElementById('con-patient-id');
  const docSelect = document.getElementById('con-doctor-id');

  if (patSelect) {
    const pRes = await fetch('/api/patients');
    const patients = await pRes.json();
    patSelect.innerHTML = patients.map(p => `<option value="${p.PID}">${p.NAME} (${p.PID})</option>`).join('');
  }

  if (docSelect) {
    const dRes = await fetch('/api/employees');
    const doctors = await dRes.json();
    docSelect.innerHTML = doctors.map(d => `<option value="${d.EID}">${d.NAME} - ${d.DEPARTMENT}</option>`).join('');
  }

  const now = new Date();
  now.setHours(now.getHours() + 1);
  now.setMinutes(0);
  document.getElementById('con-time').value = now.toISOString().slice(0, 16);
}

async function populatePrescriptionDropdowns() {
  const rxSelect = document.getElementById('rx-consultation-id');
  const res = await fetch('/api/consultations');
  const list = await res.json();
  const activeConsultations = list.filter(c => c.STATUS === 'Scheduled');
  rxSelect.innerHTML = activeConsultations.map(c => `<option value="${c.CONSULTATION_ID}">${c.CONSULTATION_ID} - ${c.PATIENT_NAME} (Dr. ${c.DOCTOR_NAME})</option>`).join('') || '<option value="">No Scheduled Consultations</option>';
}

function addMedicineRow() {
  const container = document.getElementById('rx-meds-container');
  const row = document.createElement('div');
  row.className = 'medicine-row';
  row.innerHTML = `
    <input type="text" placeholder="Medicine (e.g. Paracetamol 650mg)" class="rx-med-name" required />
    <input type="text" placeholder="Dosage (e.g. 1 Tab)" class="rx-med-dosage" value="1 Tablet" />
    <input type="text" placeholder="Freq (e.g. 2x Daily)" class="rx-med-freq" value="Twice Daily" />
    <button type="button" class="btn-danger-sm" onclick="this.parentElement.remove()"><i class="fa-solid fa-xmark"></i></button>
  `;
  container.appendChild(row);
}

async function handleAddEmployee(e) {
  e.preventDefault();
  const data = {
    EID: document.getElementById('emp-eid').value.trim(),
    NAME: document.getElementById('emp-name').value.trim(),
    DEPARTMENT: document.getElementById('emp-dept').value.trim(),
    MOBILE_NO: document.getElementById('emp-mobile').value.trim(),
    AGE: parseInt(document.getElementById('emp-age').value),
    GENDER: document.getElementById('emp-gender').value,
    SALARY: parseFloat(document.getElementById('emp-salary').value)
  };

  const res = await fetch('/api/employees', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-employee');
    loadEmployees();
  } else {
    showToast(resData.error, 'error');
  }
}

async function handleAddPatient(e) {
  e.preventDefault();
  const data = {
    NAME: document.getElementById('pat-name').value.trim(),
    ISSUE: document.getElementById('pat-issue').value.trim(),
    AGE: parseInt(document.getElementById('pat-age').value),
    GENDER: document.getElementById('pat-gender').value,
    FEES: parseFloat(document.getElementById('pat-fees').value),
    MOBILE_NO: document.getElementById('pat-mobile').value.trim()
  };

  const res = await fetch('/api/patients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-patient');
    loadPatients();
  } else {
    showToast(resData.error, 'error');
  }
}

async function handleBookConsultation(e) {
  e.preventDefault();
  const data = {
    PATIENT_ID: document.getElementById('con-patient-id')?.value,
    EMP_ID: document.getElementById('con-doctor-id').value,
    REASON: document.getElementById('con-reason').value.trim(),
    FEES: parseFloat(document.getElementById('con-fee').value),
    TIME: document.getElementById('con-time').value.replace('T', ' ')
  };

  const res = await fetch('/api/consultations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-consultation');
    loadConsultations();
  } else {
    showToast(resData.error, 'error');
  }
}

async function handleCreatePrescription(e) {
  e.preventDefault();
  const rows = document.querySelectorAll('.medicine-row');
  const medicines = [];
  rows.forEach(r => {
    medicines.push({
      name: r.querySelector('.rx-med-name').value.trim(),
      dosage: r.querySelector('.rx-med-dosage').value.trim(),
      frequency: r.querySelector('.rx-med-freq').value.trim(),
      duration: '5 Days'
    });
  });

  const data = {
    CONSULTATION_ID: document.getElementById('rx-consultation-id').value,
    DIAGNOSIS: document.getElementById('rx-diagnosis').value.trim(),
    INSTRUCTIONS: document.getElementById('rx-instructions').value.trim(),
    MEDICINES: medicines
  };

  const res = await fetch('/api/prescriptions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-prescription');
    switchView('prescriptions');
  } else {
    showToast(resData.error, 'error');
  }
}

async function handleAddMedicine(e) {
  e.preventDefault();
  const data = {
    MEDICINE_NAME: document.getElementById('med-name').value.trim(),
    MEDICINE_TYPE: document.getElementById('med-type').value,
    STOCK: parseInt(document.getElementById('med-stock').value),
    PRICE: parseFloat(document.getElementById('med-price').value)
  };

  const res = await fetch('/api/pharmacy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-medicine');
    loadPharmacy();
  } else {
    showToast(resData.error, 'error');
  }
}

async function handleAddEmt(e) {
  e.preventDefault();
  const data = {
    VNO: document.getElementById('emt-vno').value.trim(),
    VTYPE: document.getElementById('emt-vtype').value,
    DRIVER_NAME: document.getElementById('emt-driver').value.trim(),
    MOBILE_NO: document.getElementById('emt-mobile').value.trim(),
    STATUS: 'Available'
  };

  const res = await fetch('/api/emt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  const resData = await res.json();
  if (res.ok) {
    showToast(resData.message, 'success');
    closeModal('modal-add-emt');
    loadEmt();
  } else {
    showToast(resData.error, 'error');
  }
}

async function updateEmtStatus(vno, status) {
  try {
    const res = await fetch(`/api/emt/${vno}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ STATUS: status })
    });
    if (res.ok) showToast(`Ambulance ${vno} status set to ${status}`, 'success');
  } catch (err) {
    showToast('Failed to update ambulance status', 'error');
  }
}

async function promptRestock(name, currentStock) {
  const newStock = prompt(`Update stock units for ${name}:`, currentStock);
  if (newStock !== null && !isNaN(newStock)) {
    await fetch(`/api/pharmacy/${encodeURIComponent(name)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ STOCK: parseInt(newStock) })
    });
    showToast(`Stock updated for ${name}`, 'success');
    loadPharmacy();
  }
}

async function deleteEmployee(eid) {
  if (confirm(`Are you sure you want to remove Employee ${eid}?`)) {
    const res = await fetch(`/api/employees/${eid}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, 'success');
      loadEmployees();
    } else {
      showToast(data.error, 'error');
    }
  }
}

async function deletePatient(pid) {
  if (confirm(`Are you sure you want to delete patient ${pid}?`)) {
    const res = await fetch(`/api/patients/${pid}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message, 'success');
      loadPatients();
    } else {
      showToast(data.error, 'error');
    }
  }
}

async function resetDatabasePrompt() {
  if (confirm('Reset hospital database with fresh demo data?')) {
    const res = await fetch('/api/admin/reset', { method: 'POST' });
    const data = await res.json();
    showToast(data.message, 'success');
    loadDashboardData();
  }
}

function filterTable(tableId, query) {
  const q = query.toLowerCase();
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function filterPrescriptions(query) {
  const q = query.toLowerCase();
  document.querySelectorAll('.prescription-card').forEach(card => {
    card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<i class="fa-solid fa-circle-info"></i> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
