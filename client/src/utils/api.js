/**
 * Centralized API Client for Lead CRM Backend
 */

const API_BASE = '/api';

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/dashboard/stats`);
  if (!res.ok) throw new Error('Failed to fetch dashboard stats');
  return await res.json();
}

export async function fetchLeads(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  });

  const res = await fetch(`${API_BASE}/leads?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch leads');
  return await res.json();
}

export async function fetchLeadById(id) {
  const res = await fetch(`${API_BASE}/leads/${id}`);
  if (!res.ok) throw new Error('Lead not found');
  return await res.json();
}

export async function createLead(leadData) {
  const res = await fetch(`${API_BASE}/leads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(leadData),
  });
  if (!res.ok) throw new Error('Failed to create lead');
  return await res.json();
}

export async function updateLead(id, leadData) {
  const res = await fetch(`${API_BASE}/leads/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(leadData),
  });
  if (!res.ok) throw new Error('Failed to update lead');
  return await res.json();
}

export async function deleteLead(id) {
  const res = await fetch(`${API_BASE}/leads/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete lead');
  return await res.json();
}

export async function executeBulkAction(action, leadIds, payload = {}) {
  const res = await fetch(`${API_BASE}/leads/bulk-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, lead_ids: leadIds, payload }),
  });
  if (!res.ok) throw new Error('Failed to execute bulk action');
  return await res.json();
}

export async function previewImportFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/import/preview`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || 'Failed to parse file for preview');
  }
  return await res.json();
}

export async function confirmImport(importPayload) {
  const res = await fetch(`${API_BASE}/import/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(importPayload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || 'Failed to import clean data');
  }
  return await res.json();
}

export async function fetchFilterOptions() {
  const res = await fetch(`${API_BASE}/filters/options`);
  if (!res.ok) throw new Error('Failed to fetch filter options');
  return await res.json();
}

export function getExportUrl(format = 'excel', params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  });
  return `${API_BASE}/export/${format}?${query.toString()}`;
}

export async function exportSelectedLeads(format = 'excel', leadIds = []) {
  const res = await fetch(`${API_BASE}/export/${format}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lead_ids: leadIds }),
  });
  if (!res.ok) throw new Error('Failed to export leads');

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `TechvionNova_Selected_Leads_${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : 'csv'}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
