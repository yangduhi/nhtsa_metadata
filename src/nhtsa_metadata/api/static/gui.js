const state = {
  limit: 50,
  offset: 0,
  total: 0,
  jobStatus: '',
};

const elements = {
  apiStatus: document.querySelector('#apiStatus'),
  environmentStatus: document.querySelector('#environmentStatus'),
  assetCountStatus: document.querySelector('#assetCountStatus'),
  jobCountStatus: document.querySelector('#jobCountStatus'),
  assetRows: document.querySelector('#assetRows'),
  jobRows: document.querySelector('#jobRows'),
  filterForm: document.querySelector('#assetFilterForm'),
  testNoInput: document.querySelector('#testNoInput'),
  assetKindInput: document.querySelector('#assetKindInput'),
  assetSearchInput: document.querySelector('#assetSearchInput'),
  pageStatus: document.querySelector('#pageStatus'),
  toast: document.querySelector('#toast'),
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json();
}

function assetQueryParams() {
  const params = new URLSearchParams();
  const testNo = elements.testNoInput.value.trim();
  const kind = elements.assetKindInput.value.trim();
  const q = elements.assetSearchInput.value.trim();
  params.set('limit', String(state.limit));
  params.set('offset', String(state.offset));
  if (testNo) params.set('test_no', testNo);
  if (kind) params.set('asset_kind', kind);
  if (q) params.set('q', q);
  return params;
}

async function loadHealth() {
  try {
    const data = await fetchJson('/api/health');
    elements.apiStatus.textContent = data.status || 'ok';
    elements.environmentStatus.textContent = data.environment || 'local';
  } catch (error) {
    elements.apiStatus.textContent = 'offline';
    elements.environmentStatus.textContent = 'error';
    showToast(`Health check failed: ${error.message}`);
  }
}

async function loadAssets() {
  elements.assetRows.innerHTML = '<tr><td colspan="5" class="empty-cell">Loading assets…</td></tr>';
  try {
    const data = await fetchJson('/api/download-assets?' + assetQueryParams().toString());
    state.total = data.total || data.count || 0;
    renderAssets(data.items || []);
    updateAssetStatus(data);
  } catch (error) {
    elements.assetRows.innerHTML = `<tr><td colspan="5" class="empty-cell">${escapeHtml(error.message)}</td></tr>`;
    showToast(`Asset load failed: ${error.message}`);
  }
}

function updateAssetStatus(data) {
  const count = data.count || 0;
  const total = data.total || count;
  elements.assetCountStatus.textContent = `${count} / ${total}`;
  const page = Math.floor(state.offset / state.limit) + 1;
  const pages = Math.max(1, Math.ceil(total / state.limit));
  elements.pageStatus.textContent = `Page ${page} of ${pages}`;
}

function renderAssets(items) {
  if (!items.length) {
    elements.assetRows.innerHTML = '<tr><td colspan="5" class="empty-cell">No assets match the current filters.</td></tr>';
    return;
  }
  elements.assetRows.innerHTML = items.map((asset) => {
    const queuedJobId = asset.queued_job_id;
    const queuedJobStatus = asset.queued_job_status || 'queued';
    const isQueued = queuedJobId !== null && queuedJobId !== undefined;
    const action = isQueued
      ? `<button class="button ghost" type="button" disabled title="Already ${escapeHtml(queuedJobStatus)} as job #${escapeHtml(queuedJobId)}">Queued #${escapeHtml(queuedJobId)}</button>`
      : `<button class="button ghost" type="button" data-action="queueAsset" data-asset-id="${asset.id}">Queue</button>`;
    return `
    <tr>
      <td><strong>${escapeHtml(asset.test_no)}</strong></td>
      <td><span class="asset-kind">${escapeHtml(asset.asset_kind || 'unknown')}</span></td>
      <td class="file-cell" title="${escapeHtml(asset.suggested_filename || '')}">${escapeHtml(asset.suggested_filename || 'asset_' + asset.id)}</td>
      <td class="url-cell" title="${escapeHtml(asset.source_url || '')}">${escapeHtml(asset.source_url || '—')}</td>
      <td class="right">${action}</td>
    </tr>`;
  }).join('');
}

async function createDownloadJob(assetId) {
  try {
    const job = await fetchJson('/api/download-jobs', {
      method: 'POST',
      body: JSON.stringify({ media_asset_id: Number(assetId) }),
    });
    if (job.already_queued) {
      showToast(`Already queued as job #${job.id}`);
    } else {
      showToast(`Queued ${job.filename || 'asset'} as job #${job.id}`);
    }
    await Promise.all([loadJobs(), loadAssets()]);
  } catch (error) {
    showToast(`Queue failed: ${error.message}`);
  }
}

async function loadJobs() {
  const params = new URLSearchParams();
  if (state.jobStatus) params.set('status', state.jobStatus);
  try {
    const data = await fetchJson('/api/download-jobs' + (params.toString() ? '?' + params.toString() : ''));
    renderJobs(data.items || []);
    const queued = (data.items || []).filter((job) => job.status === 'queued').length;
    elements.jobCountStatus.textContent = `${queued} queued`;
  } catch (error) {
    elements.jobRows.innerHTML = `<div class="empty-card">${escapeHtml(error.message)}</div>`;
    showToast(`Job load failed: ${error.message}`);
  }
}

function renderJobs(items) {
  if (!items.length) {
    elements.jobRows.innerHTML = '<div class="empty-card">No jobs for this filter.</div>';
    return;
  }
  elements.jobRows.innerHTML = items.map((job) => {
    const canRun = job.status === 'queued' || job.status === 'failed';
    return `
      <article class="job-card">
        <div>
          <p class="job-title">${escapeHtml(job.filename || 'download job #' + job.id)}</p>
          <p class="job-meta">
            <span>#${job.id}</span>
            <span>test ${escapeHtml(job.test_no || '—')}</span>
            <span>${formatBytes(job.size_bytes)}</span>
            <span title="${escapeHtml(job.destination_path || '')}">${escapeHtml(job.destination_path || 'not written')}</span>
          </p>
        </div>
        <div class="job-actions">
          <span class="job-status ${escapeHtml(job.status || '')}">${escapeHtml(job.status || 'unknown')}</span>
          ${canRun ? `<button class="button danger" type="button" data-action="runJob" data-job-id="${job.id}">Run</button>` : ''}
        </div>
      </article>`;
  }).join('');
}

async function runDownloadJob(jobId) {
  const approved = window.confirm('이 job을 실행하면 실제 HTTP(S) 다운로드가 시작될 수 있습니다. 계속할까요?');
  if (!approved) return;
  try {
    const job = await fetchJson(`/api/download-jobs/${jobId}/run`, { method: 'POST' });
    showToast(`Job #${job.id} ${job.status}`);
    await loadJobs();
  } catch (error) {
    showToast(`Run failed: ${error.message}`);
    await loadJobs();
  }
}

function bindEvents() {
  elements.filterForm.addEventListener('submit', (event) => {
    event.preventDefault();
    state.offset = 0;
    loadAssets();
  });

  document.addEventListener('click', (event) => {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    const action = target.dataset.action;
    if (action === 'queueAsset') createDownloadJob(target.dataset.assetId);
    if (action === 'runJob') runDownloadJob(target.dataset.jobId);
    if (action === 'refreshAll') refreshAll();
    if (action === 'focusSearch') elements.assetSearchInput.focus();
    if (action === 'nextPage') {
      if (state.offset + state.limit < state.total) {
        state.offset += state.limit;
        loadAssets();
      }
    }
    if (action === 'previousPage') {
      state.offset = Math.max(0, state.offset - state.limit);
      loadAssets();
    }
  });

  document.querySelectorAll('[data-status]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-status]').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      state.jobStatus = button.dataset.status || '';
      loadJobs();
    });
  });
}

function refreshAll() {
  loadHealth();
  loadAssets();
  loadJobs();
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => elements.toast.classList.remove('show'), 3600);
}

function formatBytes(value) {
  if (!value) return 'size unknown';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = Number(value);
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

bindEvents();
refreshAll();
