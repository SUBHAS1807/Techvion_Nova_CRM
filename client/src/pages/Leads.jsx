import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Filter,
  Download,
  Trash2,
  CheckSquare,
  Square,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Edit2,
  AlertTriangle,
  FileSpreadsheet,
  CheckCircle2,
  MoreHorizontal,
  X,
  RefreshCw,
  Plus
} from 'lucide-react';
import {
  fetchLeads,
  updateLead,
  deleteLead,
  executeBulkAction,
  fetchFilterOptions,
  exportSelectedLeads,
  getExportUrl
} from '../utils/api';
import LeadModal from '../components/LeadModal';

export default function Leads() {
  const [searchParams, setSearchParams] = useSearchParams();

  // State for Leads & Pagination
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 25,
    totalRecords: 0,
    totalPages: 1,
  });

  // Sorting
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('DESC');

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [showFilters, setShowFilters] = useState(false);
  const [filterOptions, setFilterOptions] = useState({
    cities: [],
    states: [],
    countries: [],
    industries: [],
    sources: [],
    statuses: [],
    websiteStatuses: [],
    emailStatuses: [],
  });

  const [filters, setFilters] = useState({
    website_status: searchParams.get('website_status') || '',
    has_website: searchParams.get('has_website') || '',
    email_status: searchParams.get('email_status') || '',
    lead_status: searchParams.get('lead_status') || '',
    lead_source: searchParams.get('lead_source') || '',
    data_quality: searchParams.get('data_quality') || '',
    city: searchParams.get('city') || '',
    state: searchParams.get('state') || '',
    country: searchParams.get('country') || '',
    industry: searchParams.get('industry') || '',
    needs_verification: searchParams.get('needs_verification') || '',
    is_verified: searchParams.get('is_verified') || '',
  });

  // Multi-Selection State
  const [selectedIds, setSelectedIds] = useState([]);

  // Modal State
  const [activeLead, setActiveLead] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Bulk Action Drawer State
  const [bulkAction, setBulkAction] = useState('');
  const [bulkPayload, setBulkPayload] = useState({});
  const [bulkLoading, setBulkLoading] = useState(false);

  // Fetch filter options on load
  useEffect(() => {
    fetchFilterOptions()
      .then((res) => {
        if (res.success) setFilterOptions(res);
      })
      .catch(console.error);
  }, []);

  // Fetch leads based on current state
  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        page: pagination.page,
        limit: pagination.limit,
        search: searchTerm,
        sortBy,
        sortOrder,
        ...filters,
      };

      const res = await fetchLeads(params);
      if (res.success) {
        setLeads(res.data);
        setPagination((prev) => ({
          ...prev,
          totalRecords: res.pagination.totalRecords,
          totalPages: res.pagination.totalPages,
        }));
      }
    } catch (err) {
      setError(err.message || 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.limit, searchTerm, sortBy, sortOrder, filters]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // Handle lead saved or updated globally
  useEffect(() => {
    const handleLeadUpdated = () => loadLeads();
    window.addEventListener('lead-updated', handleLeadUpdated);
    window.addEventListener('refresh-leads', handleLeadUpdated);
    return () => {
      window.removeEventListener('lead-updated', handleLeadUpdated);
      window.removeEventListener('refresh-leads', handleLeadUpdated);
    };
  }, [loadLeads]);

  // Debounced search
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPagination((prev) => ({ ...prev, page: 1 }));
    loadLeads();
  };

  // Sort handler
  const handleSort = (colKey) => {
    if (sortBy === colKey) {
      setSortOrder((prev) => (prev === 'ASC' ? 'DESC' : 'ASC'));
    } else {
      setSortBy(colKey);
      setSortOrder('ASC');
    }
  };

  // Selection handlers
  const handleSelectAll = () => {
    if (selectedIds.length === leads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(leads.map((l) => l.lead_id));
    }
  };

  const handleToggleSelect = (leadId) => {
    setSelectedIds((prev) =>
      prev.includes(leadId) ? prev.filter((id) => id !== leadId) : [...prev, leadId]
    );
  };

  // Inline status quick-change
  const handleInlineStatusChange = async (leadId, newStatus) => {
    try {
      await updateLead(leadId, { lead_status: newStatus });
      setLeads((prev) =>
        prev.map((l) => (l.lead_id === leadId ? { ...l, lead_status: newStatus } : l))
      );
    } catch (err) {
      alert('Failed to update status: ' + err.message);
    }
  };

  // Quick Inline Verify
  const handleInlineVerify = async (leadId) => {
    try {
      await updateLead(leadId, { is_verified: true, needs_verification: false });
      setLeads((prev) =>
        prev.map((l) =>
          l.lead_id === leadId
            ? { ...l, is_verified: 1, needs_verification: 0, data_quality: 'High' }
            : l
        )
      );
    } catch (err) {
      alert('Failed to verify lead: ' + err.message);
    }
  };

  // Execute Bulk Action
  const handleRunBulkAction = async () => {
    if (!bulkAction || selectedIds.length === 0) return;

    if (bulkAction === 'delete') {
      if (!window.confirm(`Permanently delete ${selectedIds.length} selected leads?`)) {
        return;
      }
    }

    setBulkLoading(true);
    try {
      await executeBulkAction(bulkAction, selectedIds, bulkPayload);
      setSelectedIds([]);
      setBulkAction('');
      setBulkPayload({});
      loadLeads();
    } catch (err) {
      alert('Bulk action error: ' + err.message);
    } finally {
      setBulkLoading(false);
    }
  };

  // Export handlers
  const handleExportFiltered = (format = 'excel') => {
    const params = {
      search: searchTerm,
      ...filters,
    };
    window.open(getExportUrl(format, params), '_blank');
  };

  const handleExportSelected = (format = 'excel') => {
    if (selectedIds.length === 0) {
      alert('Please select at least one lead to export.');
      return;
    }
    exportSelectedLeads(format, selectedIds);
  };

  const resetFilters = () => {
    setFilters({
      website_status: '',
      has_website: '',
      email_status: '',
      lead_status: '',
      lead_source: '',
      data_quality: '',
      city: '',
      state: '',
      country: '',
      industry: '',
      needs_verification: '',
      is_verified: '',
    });
    setSearchTerm('');
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (searchTerm ? 1 : 0);

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
            <span>Leads Directory</span>
            <span className="text-xs bg-black text-white px-2 py-0.5 rounded-full font-mono font-medium">
              {pagination.totalRecords} leads
            </span>
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Manage, verify, filter, and track business prospects in real time.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setActiveLead(null);
              setIsModalOpen(true);
            }}
            className="btn-primary text-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Add Lead</span>
          </button>

          {/* Export Dropdown */}
          <div className="relative group">
            <button className="btn-secondary text-xs flex items-center gap-1.5">
              <Download className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
            <div className="absolute right-0 mt-1 w-48 bg-white border border-neutral-200 rounded-lg shadow-lg py-1 hidden group-hover:block z-30">
              <button
                onClick={() => handleExportFiltered('excel')}
                className="w-full text-left px-3 py-2 text-xs text-neutral-800 hover:bg-neutral-100 flex items-center justify-between font-medium"
              >
                <span>Export Filtered (Excel)</span>
                <span className="font-mono text-[10px] text-neutral-400">.xlsx</span>
              </button>
              <button
                onClick={() => handleExportFiltered('csv')}
                className="w-full text-left px-3 py-2 text-xs text-neutral-800 hover:bg-neutral-100 flex items-center justify-between font-medium"
              >
                <span>Export Filtered (CSV)</span>
                <span className="font-mono text-[10px] text-neutral-400">.csv</span>
              </button>
              {selectedIds.length > 0 && (
                <>
                  <div className="border-t border-neutral-100 my-1"></div>
                  <button
                    onClick={() => handleExportSelected('excel')}
                    className="w-full text-left px-3 py-2 text-xs text-black font-semibold hover:bg-neutral-100 flex items-center justify-between"
                  >
                    <span>Export {selectedIds.length} Selected (Excel)</span>
                  </button>
                  <button
                    onClick={() => handleExportSelected('csv')}
                    className="w-full text-left px-3 py-2 text-xs text-black font-semibold hover:bg-neutral-100 flex items-center justify-between"
                  >
                    <span>Export {selectedIds.length} Selected (CSV)</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-neutral-200 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by Business Name, Email, Phone, Website, City, State, Country..."
              className="w-full pl-9 pr-20 py-2 bg-neutral-50 border border-neutral-200 rounded-lg text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-black transition-all"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => {
                  setSearchTerm('');
                  setPagination((prev) => ({ ...prev, page: 1 }));
                }}
                className="absolute right-14 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-black text-xs"
              >
                Clear
              </button>
            )}
            <button
              type="submit"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 px-2.5 py-1 bg-black text-white text-[11px] font-semibold rounded-md hover:bg-neutral-800"
            >
              Search
            </button>
          </form>

          {/* Toggle Filter Panel Button */}
          <button
            onClick={() => setShowFilters((prev) => !prev)}
            className={`btn-secondary text-xs flex items-center gap-2 shrink-0 ${
              activeFilterCount > 0 ? 'border-black font-bold' : ''
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="bg-black text-white text-[10px] px-1.5 py-0.2 rounded-full font-mono">
                {activeFilterCount}
              </span>
            )}
          </button>

          {activeFilterCount > 0 && (
            <button
              onClick={resetFilters}
              className="text-xs text-neutral-500 hover:text-black font-semibold shrink-0"
            >
              Reset All
            </button>
          )}
        </div>

        {/* Expandable Filter Grid */}
        {showFilters && (
          <div className="pt-3 border-t border-neutral-200 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 animate-in fade-in duration-100">
            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">Website</label>
              <select
                value={filters.website_status}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, website_status: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Websites</option>
                <option value="No Website">No Website (Lead Opp)</option>
                <option value="Working">Working</option>
                <option value="Broken">Broken</option>
                <option value="Poor Website">Poor Website</option>
                <option value="Under Construction">Under Construction</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">Email Status</label>
              <select
                value={filters.email_status}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, email_status: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Emails</option>
                <option value="Valid">Valid</option>
                <option value="Invalid">Invalid</option>
                <option value="Missing">Missing</option>
                <option value="Risky">Risky</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">Lead Status</label>
              <select
                value={filters.lead_status}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, lead_status: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Statuses</option>
                {filterOptions.statuses?.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">City</label>
              <select
                value={filters.city}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, city: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Cities</option>
                {filterOptions.cities?.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">Source</label>
              <select
                value={filters.lead_source}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, lead_source: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Sources</option>
                {filterOptions.sources?.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-neutral-600 mb-1">Verification</label>
              <select
                value={filters.needs_verification}
                onChange={(e) => {
                  setFilters((prev) => ({ ...prev, needs_verification: e.target.value }));
                  setPagination((p) => ({ ...p, page: 1 }));
                }}
                className="select-field text-xs py-1.5"
              >
                <option value="">All Verification</option>
                <option value="true">⚠️ Needs Verification</option>
                <option value="false">Verified / Clean</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Bulk Actions Bar */}
      {selectedIds.length > 0 && (
        <div className="bg-neutral-950 text-white px-5 py-3 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-md animate-in slide-in-from-top-2 duration-150">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
            <span className="text-xs font-bold font-mono">
              {selectedIds.length} lead{selectedIds.length > 1 ? 's' : ''} selected
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={bulkAction}
              onChange={(e) => setBulkAction(e.target.value)}
              className="bg-neutral-900 text-white text-xs border border-neutral-700 rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-white"
            >
              <option value="">Select Bulk Action...</option>
              <option value="change_status">Change Status</option>
              <option value="change_source">Change Source</option>
              <option value="mark_verified">Mark as Verified</option>
              <option value="delete">Delete Selected</option>
            </select>

            {bulkAction === 'change_status' && (
              <select
                onChange={(e) => setBulkPayload({ status: e.target.value })}
                className="bg-neutral-900 text-white text-xs border border-neutral-700 rounded-lg px-3 py-1.5"
              >
                <option value="">Select New Status</option>
                {filterOptions.statuses?.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            )}

            {bulkAction === 'change_source' && (
              <select
                onChange={(e) => setBulkPayload({ source: e.target.value })}
                className="bg-neutral-900 text-white text-xs border border-neutral-700 rounded-lg px-3 py-1.5"
              >
                <option value="">Select New Source</option>
                {filterOptions.sources?.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={handleRunBulkAction}
              disabled={bulkLoading || !bulkAction}
              className="px-3 py-1.5 bg-white text-black text-xs font-bold rounded-lg hover:bg-neutral-200 transition-colors disabled:opacity-50"
            >
              {bulkLoading ? 'Applying...' : 'Apply Action'}
            </button>

            <button
              onClick={() => setSelectedIds([])}
              className="text-xs text-neutral-400 hover:text-white px-2"
            >
              Deselect
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-xl text-xs font-medium">
          {error}
        </div>
      )}

      {/* Leads Table Container */}
      <div className="bg-white border border-neutral-200 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto min-h-[300px]">
          <table className="w-full text-left border-collapse text-xs">
            {/* Table Header */}
            <thead className="bg-neutral-950 text-white border-b border-neutral-800">
              <tr>
                <th className="p-3 w-10 text-center">
                  <button onClick={handleSelectAll} className="p-0.5 text-neutral-400 hover:text-white">
                    {selectedIds.length > 0 && selectedIds.length === leads.length ? (
                      <CheckSquare className="w-4 h-4 text-white" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>

                <th
                  onClick={() => handleSort('business_name')}
                  className="p-3 font-semibold uppercase tracking-wider cursor-pointer select-none hover:text-neutral-300"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Business Name</span>
                    <ArrowUpDown className="w-3 h-3 text-neutral-500" />
                  </div>
                </th>

                <th className="p-3 font-semibold uppercase tracking-wider">Email</th>
                <th className="p-3 font-semibold uppercase tracking-wider">Phone</th>
                <th className="p-3 font-semibold uppercase tracking-wider">Website</th>

                <th
                  onClick={() => handleSort('city')}
                  className="p-3 font-semibold uppercase tracking-wider cursor-pointer select-none hover:text-neutral-300"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Location</span>
                    <ArrowUpDown className="w-3 h-3 text-neutral-500" />
                  </div>
                </th>

                <th className="p-3 font-semibold uppercase tracking-wider">Industry</th>

                <th
                  onClick={() => handleSort('lead_status')}
                  className="p-3 font-semibold uppercase tracking-wider cursor-pointer select-none hover:text-neutral-300"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Status</span>
                    <ArrowUpDown className="w-3 h-3 text-neutral-500" />
                  </div>
                </th>

                <th className="p-3 font-semibold uppercase tracking-wider">Source</th>
                <th className="p-3 font-semibold uppercase tracking-wider text-center">Quality</th>
                <th className="p-3 font-semibold uppercase tracking-wider text-right pr-4">Actions</th>
              </tr>
            </thead>

            {/* Table Body */}
            <tbody className="divide-y divide-neutral-200">
              {loading ? (
                <tr>
                  <td colSpan="11" className="p-12 text-center text-neutral-500 font-mono text-xs">
                    Loading CRM leads...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="11" className="p-12 text-center text-neutral-500 text-xs">
                    No leads found matching your search or filters.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => {
                  const isSelected = selectedIds.includes(lead.lead_id);
                  return (
                    <tr
                      key={lead.lead_id}
                      className={`hover:bg-neutral-50/80 transition-colors ${
                        isSelected ? 'bg-neutral-100/70' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="p-3 text-center">
                        <button
                          onClick={() => handleToggleSelect(lead.lead_id)}
                          className="p-0.5 text-neutral-500 hover:text-black"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-black" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </td>

                      {/* Business Name */}
                      <td className="p-3 font-medium text-black max-w-[220px]">
                        <button
                          onClick={() => {
                            setActiveLead(lead);
                            setIsModalOpen(true);
                          }}
                          className="font-bold text-left hover:underline block truncate"
                          title={lead.business_name}
                        >
                          {lead.business_name}
                        </button>
                        <div className="text-[10px] text-neutral-400 font-mono">
                          {lead.lead_id}
                        </div>
                      </td>

                      {/* Email & Status */}
                      <td className="p-3 max-w-[180px]">
                        {lead.email ? (
                          <div className="truncate font-mono text-[11px]" title={lead.email}>
                            {lead.email}
                          </div>
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">No Email</span>
                        )}
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded inline-block mt-0.5 ${
                            lead.email_status === 'Valid'
                              ? 'bg-neutral-900 text-white font-mono'
                              : lead.email_status === 'Invalid'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-neutral-100 text-neutral-600'
                          }`}
                        >
                          {lead.email_status || 'Unverified'}
                        </span>
                      </td>

                      {/* Phone */}
                      <td className="p-3 font-mono text-[11px] text-neutral-700 whitespace-nowrap">
                        {lead.phone || <span className="text-neutral-400 italic">No Phone</span>}
                      </td>

                      {/* Website & Status */}
                      <td className="p-3 max-w-[180px]">
                        {lead.website ? (
                          <a
                            href={lead.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-neutral-900 font-medium hover:underline flex items-center gap-1 truncate text-[11px]"
                            title={lead.website}
                          >
                            <span className="truncate">{lead.website.replace(/^https?:\/\//, '')}</span>
                            <ExternalLink className="w-3 h-3 shrink-0 text-neutral-400" />
                          </a>
                        ) : (
                          <span className="text-neutral-400 italic text-[11px]">No Website</span>
                        )}
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded inline-block mt-0.5 ${
                            lead.website_status === 'No Website'
                              ? 'bg-black text-white font-mono'
                              : lead.website_status === 'Working'
                              ? 'bg-neutral-200 text-neutral-800'
                              : lead.website_status === 'Broken'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-neutral-100 text-neutral-600'
                          }`}
                        >
                          {lead.website_status}
                        </span>
                      </td>

                      {/* Location & Verification Flag */}
                      <td className="p-3 max-w-[160px]">
                        <div className="font-medium text-neutral-900 truncate">
                          {lead.city || '—'}, {lead.state || ''}
                        </div>
                        {lead.needs_verification ? (
                          <div
                            className="inline-flex items-center gap-1 text-[10px] bg-amber-100 text-amber-900 px-1.5 py-0.2 rounded font-semibold mt-0.5 cursor-pointer"
                            title={lead.verification_reason || 'Location mismatch flagged'}
                            onClick={() => {
                              setActiveLead(lead);
                              setIsModalOpen(true);
                            }}
                          >
                            <AlertTriangle className="w-2.5 h-2.5 text-amber-700" />
                            <span>Verify</span>
                          </div>
                        ) : lead.is_verified ? (
                          <span className="text-[9px] text-neutral-500 font-mono">✓ Verified</span>
                        ) : null}
                      </td>

                      {/* Industry */}
                      <td className="p-3 text-neutral-700 truncate max-w-[130px]" title={lead.industry}>
                        {lead.industry || '—'}
                      </td>

                      {/* Lead Status (Inline Dropdown) */}
                      <td className="p-3">
                        <select
                          value={lead.lead_status}
                          onChange={(e) => handleInlineStatusChange(lead.lead_id, e.target.value)}
                          className="bg-neutral-100 hover:bg-neutral-200 text-neutral-900 text-xs font-semibold py-1 px-2 rounded-lg border-0 focus:ring-1 focus:ring-black cursor-pointer transition-colors"
                        >
                          {filterOptions.statuses?.map((st) => (
                            <option key={st} value={st}>
                              {st}
                            </option>
                          ))}
                        </select>
                      </td>

                      {/* Source */}
                      <td className="p-3 text-neutral-600 text-[11px] whitespace-nowrap">
                        {lead.lead_source}
                      </td>

                      {/* Data Quality */}
                      <td className="p-3 text-center">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                            lead.data_quality === 'High'
                              ? 'bg-black text-white'
                              : lead.data_quality === 'Medium'
                              ? 'bg-neutral-300 text-black'
                              : 'bg-neutral-100 text-neutral-500'
                          }`}
                        >
                          {lead.data_quality}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="p-3 text-right pr-4">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setActiveLead(lead);
                              setIsModalOpen(true);
                            }}
                            title="Edit Lead"
                            className="p-1.5 text-neutral-600 hover:text-black hover:bg-neutral-200 rounded-lg transition-colors"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={async () => {
                              if (window.confirm(`Delete lead "${lead.business_name}"?`)) {
                                await deleteLead(lead.lead_id);
                                loadLeads();
                              }
                            }}
                            title="Delete Lead"
                            className="p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-4 border-t border-neutral-200 bg-white flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-neutral-600">
          <div className="flex items-center gap-2">
            <span>Showing</span>
            <span className="font-mono font-bold text-black">
              {leads.length > 0 ? (pagination.page - 1) * pagination.limit + 1 : 0}
            </span>
            <span>to</span>
            <span className="font-mono font-bold text-black">
              {Math.min(pagination.page * pagination.limit, pagination.totalRecords)}
            </span>
            <span>of</span>
            <span className="font-mono font-bold text-black">{pagination.totalRecords}</span>
            <span>leads</span>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={pagination.limit}
              onChange={(e) => {
                setPagination((p) => ({ ...p, limit: parseInt(e.target.value, 10), page: 1 }));
              }}
              className="bg-neutral-50 border border-neutral-300 text-xs rounded-lg px-2 py-1 focus:ring-1 focus:ring-black"
            >
              <option value="15">15 per page</option>
              <option value="25">25 per page</option>
              <option value="50">50 per page</option>
              <option value="100">100 per page</option>
            </select>

            <button
              onClick={() => setPagination((p) => ({ ...p, page: Math.max(1, p.page - 1) }))}
              disabled={pagination.page <= 1}
              className="p-1.5 bg-neutral-100 hover:bg-neutral-200 disabled:opacity-40 rounded-lg text-black transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="font-mono text-xs font-bold text-black px-2">
              Page {pagination.page} / {pagination.totalPages || 1}
            </span>

            <button
              onClick={() => setPagination((p) => ({ ...p, page: Math.min(pagination.totalPages, p.page + 1) }))}
              disabled={pagination.page >= pagination.totalPages}
              className="p-1.5 bg-neutral-100 hover:bg-neutral-200 disabled:opacity-40 rounded-lg text-black transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Lead Edit / View / Create Modal */}
      <LeadModal
        isOpen={isModalOpen}
        lead={activeLead}
        onClose={() => {
          setIsModalOpen(false);
          setActiveLead(null);
        }}
        onSaveSuccess={() => {
          loadLeads();
        }}
        onDeleteSuccess={() => {
          loadLeads();
        }}
      />
    </div>
  );
}
