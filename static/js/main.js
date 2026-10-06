/**
 * RetailTwin AI — Global JavaScript Utilities
 */

// ─── API Helper ───────────────────────────────────────────────────────────────

async function apiRequest(method, url, body = null) {
  const opts = {
    method: method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return res.json();
}

// ─── Toast Notification ───────────────────────────────────────────────────────

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || createToastContainer();
  const id = 'toast-' + Date.now();
  const icons = { success: 'bi-check-circle-fill', danger: 'bi-x-circle-fill',
                  warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  const html = `
    <div id="${id}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="bi ${icons[type]||'bi-bell'} me-2"></i>${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
  const el = document.getElementById(id);
  new bootstrap.Toast(el, { delay: 4000 }).show();
  el.addEventListener('hidden.bs.toast', () => el.remove());
}

function createToastContainer() {
  const div = document.createElement('div');
  div.id = 'toast-container';
  div.className = 'toast-container position-fixed top-0 end-0 p-3';
  div.style.zIndex = '9999';
  document.body.appendChild(div);
  return div;
}

// ─── Confirm Dialog ───────────────────────────────────────────────────────────

function confirmDelete(message = 'Are you sure you want to delete this item? This cannot be undone.') {
  return confirm(message);
}

// ─── Format Currency ─────────────────────────────────────────────────────────

function formatCurrency(amount) {
  return '₹' + parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 });
}

// ─── Format Date ─────────────────────────────────────────────────────────────

function formatDate(isoStr) {
  if (!isoStr) return '';
  return isoStr.substring(0, 10);
}

// ─── Stock Status Badge ───────────────────────────────────────────────────────

function stockStatusBadge(status) {
  const map = {
    'NORMAL':      '<span class="badge bg-success">Normal</span>',
    'LOW_STOCK':   '<span class="badge bg-warning text-dark">Low Stock</span>',
    'OVERSTOCK':   '<span class="badge bg-info text-dark">Overstock</span>',
    'OUT_OF_STOCK':'<span class="badge bg-danger">Out of Stock</span>',
  };
  return map[status] || `<span class="badge bg-secondary">${status}</span>`;
}

// ─── Handle API Error ─────────────────────────────────────────────────────────

function handleApiError(json, fallback = 'An error occurred.') {
  const msg = (json && json.message) ? json.message : fallback;
  showToast(msg, 'danger');
}

// ─── Populate Select ──────────────────────────────────────────────────────────

function populateSelect(selectId, items, valueKey, labelKey, placeholder = 'Select...') {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = `<option value="">${placeholder}</option>` +
    items.map(i => `<option value="${i[valueKey]}">${i[labelKey]}</option>`).join('');
}

// ─── Auto-dismiss alerts ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
  setTimeout(() => {
    // Only auto-dismiss flash message alerts, not permanent UI alert panels
    document.querySelectorAll('.alert.alert-success[data-auto-dismiss]').forEach(el => {
      const bs = bootstrap.Alert.getOrCreateInstance(el);
      bs.close();
    });
  }, 5000);
});
