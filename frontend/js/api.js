/* ═══════════════════════════════════════════════════════════════════════
   TechvionNova CRM – API Client, SVG Icons & UI Component Helpers
   ═══════════════════════════════════════════════════════════════════════ */

const API_BASE = '';  // same-origin

const api = {
    // ── Google Places API (New) ───────────────────────────────────────
    async getGoogleStatus() {
        const res = await fetch(`${API_BASE}/api/google-places/status`);
        if (!res.ok) throw new Error('Failed to fetch Google API status');
        return res.json();
    },

    async testGoogleConnection() {
        const res = await fetch(`${API_BASE}/api/google-places/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        return res.json();
    },

    async saveGoogleApiKey(key) {
        const res = await fetch(`${API_BASE}/api/google-places/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: key }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || 'Failed to save API key');
        }
        return res.json();
    },

    async searchPlaces(params) {
        const res = await fetch(`${API_BASE}/api/google-places/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || `Search failed: ${res.statusText}`);
        }
        return data;
    },

    async importPlace(placeData, updateExisting = false) {
        const res = await fetch(`${API_BASE}/api/google-places/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ place: placeData, update_existing: updateExisting }),
        });
        const data = await res.json();
        if (res.status === 409) {
            return { duplicate: true, ...data };
        }
        if (!res.ok) {
            throw new Error(data.error || 'Import failed');
        }
        return data;
    },

    async importBulkPlaces(places, updateExisting = false) {
        const res = await fetch(`${API_BASE}/api/google-places/import-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ places, update_existing: updateExisting }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Bulk import failed');
        return data;
    },

    // ── Collection Jobs ──────────────────────────────────────────────
    async getCollectionJobs() {
        const res = await fetch(`${API_BASE}/api/collection-jobs`);
        return res.json();
    },

    async startCollectionJob(params) {
        const res = await fetch(`${API_BASE}/api/collection-jobs/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        return res.json();
    },

    async stopCollectionJob(jobId) {
        const res = await fetch(`${API_BASE}/api/collection-jobs/${jobId}/stop`, {
            method: 'POST',
        });
        return res.json();
    },

    async getJobLogs(jobId) {
        const res = await fetch(`${API_BASE}/api/collection-jobs/${jobId}/logs`);
        return res.json();
    },

    // ── Global (Worldwide) Collector ─────────────────────────────────
    async getGlobalMeta(country = '') {
        const qs = country ? `?country=${encodeURIComponent(country)}` : '';
        const res = await fetch(`${API_BASE}/api/global/meta${qs}`);
        if (!res.ok) throw new Error('Failed to load global metadata');
        return res.json();
    },

    async startGlobalJob(params) {
        const res = await fetch(`${API_BASE}/api/global/jobs/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to start global job');
        return data;
    },

    async getGlobalJobs(limit = 25) {
        const res = await fetch(`${API_BASE}/api/global/jobs?limit=${limit}`);
        return res.json();
    },

    async getGlobalJob(jobId) {
        const res = await fetch(`${API_BASE}/api/global/jobs/${jobId}`);
        if (!res.ok) throw new Error('Job not found');
        return res.json();
    },

    async globalJobAction(jobId, action) {
        const res = await fetch(`${API_BASE}/api/global/jobs/${jobId}/${action}`, {
            method: 'POST',
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `Failed to ${action} job`);
        return data;
    },

    async getGlobalDiscoveries(params = {}) {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params)) {
            if (v !== undefined && v !== null && v !== '') qs.set(k, v);
        }
        const res = await fetch(`${API_BASE}/api/global/discoveries?${qs.toString()}`);
        if (!res.ok) throw new Error('Failed to load discoveries');
        return res.json();
    },

    async getGlobalStats() {
        const res = await fetch(`${API_BASE}/api/global/stats`);
        if (!res.ok) throw new Error('Failed to load global stats');
        return res.json();
    },

    exportGlobalUrl(format = 'csv', country = '') {
        const suffix = format === 'excel' ? '/excel' : '/csv';
        const qs = country ? `?country=${encodeURIComponent(country)}` : '';
        return `${API_BASE}/api/leads/export/global${suffix}${qs}`;
    },

    // ── Leads CRUD & Filters ─────────────────────────────────────────
    async getLeads(params = {}) {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params)) {
            if (v !== undefined && v !== null && v !== '') {
                qs.set(k, v);
            }
        }
        const res = await fetch(`${API_BASE}/api/leads?${qs.toString()}`);
        if (!res.ok) throw new Error(`Failed to fetch leads: ${res.statusText}`);
        return res.json();
    },

    async getLead(id) {
        const res = await fetch(`${API_BASE}/api/leads/${id}`);
        if (!res.ok) throw new Error(`Lead not found: ${id}`);
        return res.json();
    },

    async createLead(data) {
        const res = await fetch(`${API_BASE}/api/leads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Create failed: ${res.statusText}`);
        }
        return res.json();
    },

    async updateLead(id, data) {
        const res = await fetch(`${API_BASE}/api/leads/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Update failed: ${res.statusText}`);
        }
        return res.json();
    },

    async deleteLead(id, password) {
        const res = await fetch(`${API_BASE}/api/leads/${id}/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password || '' }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || `Delete failed: ${res.statusText}`);
        return data;
    },

    async bulkDelete(ids, password) {
        const res = await fetch(`${API_BASE}/api/leads/bulk-delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids, lead_ids: ids, password: password || '' }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || `Bulk delete failed: ${res.statusText}`);
        return data;
    },

    async bulkAction(ids, action, value) {
        const res = await fetch(`${API_BASE}/api/leads/bulk-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_ids: ids, action, value }),
        });
        if (!res.ok) throw new Error(`Bulk action failed: ${res.statusText}`);
        return res.json();
    },

    // ── Timeline & Outreach ──────────────────────────────────────────
    async getTimeline(leadId) {
        const res = await fetch(`${API_BASE}/api/leads/${leadId}/timeline`);
        return res.json();
    },

    async addTimelineEntry(leadId, data) {
        const res = await fetch(`${API_BASE}/api/leads/${leadId}/timeline`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    },

    // ── Follow-ups ───────────────────────────────────────────────────
    async getFollowups(filter = 'all') {
        const res = await fetch(`${API_BASE}/api/followups?filter=${filter}`);
        return res.json();
    },

    // ── Analytics ────────────────────────────────────────────────────
    async getAnalytics() {
        const res = await fetch(`${API_BASE}/api/analytics`);
        return res.json();
    },

    // ── Website Analyzer ─────────────────────────────────────────────
    async analyzeWebsite(url, leadId = null) {
        const res = await fetch(`${API_BASE}/api/website/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, lead_id: leadId }),
        });
        return res.json();
    },

    async analyzeLeadWebsite(leadId) {
        const res = await fetch(`${API_BASE}/api/analyze/lead/${leadId}`, { method: 'POST' });
        return res.json();
    },

    async analyzeBatch(leadIds) {
        const res = await fetch(`${API_BASE}/api/analyze/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_ids: leadIds }),
        });
        return res.json();
    },
};

// ── SVG Icon Helper ─────────────────────────────────────────────────
const SVG_ICONS = {
    leads: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect><path d="M9 14l2 2 4-4"></path></svg>`,
    dashboard: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>`,
    globe: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
    search: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
    jobs: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
    analyzer: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
    outreach: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>`,
    followups: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>`,
    proposals: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`,
    deals: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.42 4.58a5.4 5.4 0 0 0-7.65 0l-.77.78-.77-.78a5.4 5.4 0 0 0-7.65 7.65l.77.78L12 20.66l7.65-7.65.77-.78a5.4 5.4 0 0 0 0-7.65z"></path></svg>`,
    settings: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`,
    key: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-1.5 1.5L16 7l-1.5-1.5M19 4.5L15 8.5M10.5 13.5L3 21l3 3 7.5-7.5"></path><circle cx="16.5" cy="7.5" r="4.5"></circle></svg>`,
    bell: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>`,
    menu: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>`,
    plus: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
    external: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`,
    check: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    columns: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="12" y1="3" x2="12" y2="21"></line></svg>`,
    filter: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>`,
};

function getIcon(name) {
    return SVG_ICONS[name] || '';
}

// ── Toast notifications ─────────────────────────────────────────────

function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<span style="color:var(--success); font-weight:700;">✓</span>`;
    } else if (type === 'error') {
        iconSvg = `<span style="color:var(--danger); font-weight:700;">✕</span>`;
    } else if (type === 'warning') {
        iconSvg = `<span style="color:var(--warning); font-weight:700;">⚠</span>`;
    } else {
        iconSvg = `<span style="color:var(--info); font-weight:700;">ℹ</span>`;
    }

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ── Badge & Visual Formatters ───────────────────────────────────────

function websiteStatusBadge(status) {
    // Machine codes from the worldwide collector map to display labels
    const WS_CODE_LABELS = {
        'NO_WEBSITE':           'No Website',
        'HAS_WEBSITE':          'Good',
        'WEBSITE_INACCESSIBLE': 'Broken',
        'WEBSITE_UNKNOWN':      'Unknown',
    };
    if (status && WS_CODE_LABELS[status]) status = WS_CODE_LABELS[status];
    if (!status) return '<span class="badge badge-unknown">Unknown</span>';
    const map = {
        'No Website':          'badge-no-website',
        'Outdated':            'badge-outdated',
        'Good':                'badge-good',
        'Broken':              'badge-broken',
        'Under Construction':  'badge-under-construction',
        'E-commerce Website':  'badge-ecommerce',
        'Booking Website':     'badge-booking',
        'Unknown':             'badge-unknown',
    };
    const cls = map[status] || 'badge-unknown';
    return `<span class="badge ${cls}"><span class="badge-dot" style="background:currentColor;"></span>${status}</span>`;
}

function leadScoreBadge(score) {
    const s = parseInt(score, 10) || 0;
    let cls = 'score-level-l';
    let label = 'Low';
    if (s >= 81) { cls = 'score-level-vh'; label = 'Very High'; }
    else if (s >= 61) { cls = 'score-level-h'; label = 'High'; }
    else if (s >= 31) { cls = 'score-level-m'; label = 'Medium'; }

    return `
    <div class="score-indicator-wrap ${cls}" title="Score: ${s}/100 (${label})">
        <div class="score-track">
            <div class="score-fill" style="width: ${Math.min(100, Math.max(8, s))}%;"></div>
        </div>
        <span class="score-val">${s}</span>
    </div>`;
}

function outreachStatusBadge(status) {
    const s = status || 'Not Contacted';
    let cls = 'badge-not-contacted';
    if (s === 'Contacted') cls = 'badge-contacted';
    else if (s === 'Follow-up') cls = 'badge-followup';
    else if (s === 'Completed') cls = 'badge-completed';
    else if (s === 'Do Not Contact') cls = 'badge-dnc';
    return `<span class="badge ${cls}">${s}</span>`;
}

function dealStatusBadge(status) {
    const s = status || 'Open';
    let cls = 'badge-deal-open';
    if (s === 'Negotiation') cls = 'badge-deal-negotiation';
    else if (s === 'Won') cls = 'badge-deal-won';
    else if (s === 'Lost') cls = 'badge-deal-lost';
    return `<span class="badge ${cls}">${s}</span>`;
}

function demoBadge(isDemo) {
    return isDemo ? '<span class="badge badge-demo">DEMO</span>' : '';
}

// ── Navigation Sidebar & Mobile Helper ──────────────────────────────

function renderSidebar(activePage) {
    return `
    <div class="sidebar-backdrop" id="sidebarBackdrop" onclick="toggleSidebar(false)"></div>
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
            <div class="logo-box">T</div>
            <div class="brand-details">
                <h1>TechvionNova</h1>
                <small>Google Places CRM</small>
            </div>
        </div>
        <nav class="sidebar-nav">
            <div class="nav-section-title">Main</div>
            <a href="leads.html" class="nav-link ${activePage === 'leads' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('leads')}</span>
                <span>Leads</span>
            </a>
            <a href="dashboard.html" class="nav-link ${activePage === 'dashboard' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('dashboard')}</span>
                <span>Dashboard</span>
            </a>

            <div class="nav-section-title">Lead Generation</div>
            <a href="global.html" class="nav-link ${activePage === 'global' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('globe')}</span>
                <span>🌍 Worldwide Collector</span>
            </a>
            <a href="collect.html" class="nav-link ${activePage === 'collect' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('search')}</span>
                <span>Google Places Search</span>
            </a>
            <a href="jobs.html" class="nav-link ${activePage === 'jobs' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('jobs')}</span>
                <span>Collection Jobs</span>
            </a>
            <a href="analyzer.html" class="nav-link ${activePage === 'analyzer' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('analyzer')}</span>
                <span>Website Analyzer</span>
            </a>

            <div class="nav-section-title">Sales</div>
            <a href="leads.html?outreach=Contacted" class="nav-link ${activePage === 'outreach' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('outreach')}</span>
                <span>Outreach</span>
            </a>
            <a href="followups.html" class="nav-link ${activePage === 'followups' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('followups')}</span>
                <span>Follow-ups</span>
            </a>
            <a href="leads.html?deal=Open" class="nav-link ${activePage === 'deals' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('deals')}</span>
                <span>Deals</span>
            </a>

            <div class="nav-section-title">System</div>
            <a href="settings.html" class="nav-link ${activePage === 'settings' ? 'active' : ''}">
                <span class="nav-icon">${getIcon('settings')}</span>
                <span>Settings</span>
            </a>
            <a href="settings.html#google-api" class="nav-link">
                <span class="nav-icon">${getIcon('key')}</span>
                <span>Google API</span>
            </a>
        </nav>
        <div class="sidebar-footer">
            <span class="status-indicator"></span>
            <span>API Online & Connected</span>
        </div>
    </aside>`;
}

function toggleSidebar(forceState) {
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    if (!sidebar) return;

    if (forceState !== undefined) {
        if (forceState) {
            sidebar.classList.add('active');
            if (backdrop) backdrop.classList.add('active');
        } else {
            sidebar.classList.remove('active');
            if (backdrop) backdrop.classList.remove('active');
        }
    } else {
        sidebar.classList.toggle('active');
        if (backdrop) backdrop.classList.toggle('active');
    }
}

// ── Top Navigation Bar Helper ───────────────────────────────────────

function renderTopNav(title, subtitle, rightActionsHtml = '') {
    return `
    <header class="topbar">
        <div class="topbar-left">
            <button class="mobile-menu-btn" onclick="toggleSidebar(true)" title="Toggle Menu">
                ${getIcon('menu')}
            </button>
            <div class="page-title-group">
                <h2>${title}</h2>
                ${subtitle ? `<p>${subtitle}</p>` : ''}
            </div>
        </div>
        <div class="topbar-right">
            ${rightActionsHtml}
            <button class="icon-btn" title="Notifications" onclick="showToast('No new notifications', 'info')">
                ${getIcon('bell')}
                <span class="notif-dot"></span>
            </button>
            <div class="user-profile-menu" title="Admin Account">
                <div class="user-avatar">AD</div>
                <div class="user-info">
                    <span class="user-name">Admin</span>
                    <span class="user-role">TechvionNova HQ</span>
                </div>
            </div>
        </div>
    </header>`;
}
