import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Globe2,
  AlertOctagon,
  Download,
  Search,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Phone,
  Mail,
  Edit2
} from 'lucide-react';
import { fetchLeads, updateLead, getExportUrl } from '../utils/api';
import LeadModal from '../components/LeadModal';

function getStatusRowClasses(status) {
  switch (status) {
    case 'Contacted':
      return 'bg-emerald-50/80 hover:bg-emerald-100/60';
    case 'Follow-up':
      return 'bg-amber-50/60 hover:bg-amber-100/50';
    case 'Interested':
      return 'bg-blue-50/60 hover:bg-blue-100/50';
    case 'Meeting':
      return 'bg-violet-50/60 hover:bg-violet-100/50';
    case 'Proposal Sent':
      return 'bg-orange-50/60 hover:bg-orange-100/50';
    case 'Converted':
      return 'bg-emerald-100/60 hover:bg-emerald-200/50';
    case 'Not Interested':
      return 'bg-red-50/50 hover:bg-red-100/40';
    case 'Closed':
      return 'bg-neutral-100/60 hover:bg-neutral-200/50';
    default:
      return 'hover:bg-neutral-50';
  }
}

export default function WebsiteOpportunities() {
  const navigate = useNavigate();

  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [subFilter, setSubFilter] = useState('No Website');
  const [searchTerm, setSearchTerm] = useState('');

  const [pagination, setPagination] = useState({
    page: 1,
    limit: 25,
    totalRecords: 0,
    totalPages: 1,
  });

  const [activeLead, setActiveLead] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadOpportunities = async () => {
    setLoading(true);
    setError('');

    try {
      const params = {
        page: pagination.page,
        limit: pagination.limit,
        search: searchTerm,
        website_status: subFilter === 'all_opportunities' ? '' : subFilter,
        has_website: subFilter === 'No Website' ? 'no' : '',
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
      setError(err.message || 'Failed to load website opportunities');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOpportunities();
  }, [pagination.page, subFilter]);

  const handleInlineStatusChange = async (leadId, newStatus) => {
    try {
      await updateLead(leadId, { lead_status: newStatus });
      setLeads((prev) =>
        prev.map((l) => (l.lead_id === leadId ? { ...l, lead_status: newStatus } : l))
      );
    } catch (err) {
      alert('Error updating status: ' + err.message);
    }
  };

  const handleExportOpportunities = (format = 'excel') => {
    const params = {
      website_status: subFilter === 'all_opportunities' ? '' : subFilter,
      has_website: subFilter === 'No Website' ? 'no' : '',
    };
    window.open(getExportUrl(format, params), '_blank');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
            <Globe2 className="w-6 h-6 text-black" />
            <span>Website Opportunities Engine</span>
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Prime prospects with <strong>No Website</strong> or <strong>Broken/Poor Websites</strong> for website development sales outreach.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExportOpportunities('excel')}
            className="btn-secondary text-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Opportunities (.xlsx)</span>
          </button>
        </div>
      </div>

      {/* Target Category Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => {
            setSubFilter('No Website');
            setPagination((p) => ({ ...p, page: 1 }));
          }}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            subFilter === 'No Website'
              ? 'bg-black text-white shadow-xs'
              : 'bg-white text-neutral-700 border border-neutral-200 hover:border-black'
          }`}
        >
          🚫 Businesses Without Website
        </button>

        <button
          onClick={() => {
            setSubFilter('Broken');
            setPagination((p) => ({ ...p, page: 1 }));
          }}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            subFilter === 'Broken'
              ? 'bg-black text-white shadow-xs'
              : 'bg-white text-neutral-700 border border-neutral-200 hover:border-black'
          }`}
        >
          ⚠️ Broken Websites (404 / Offline)
        </button>

        <button
          onClick={() => {
            setSubFilter('Poor Website');
            setPagination((p) => ({ ...p, page: 1 }));
          }}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            subFilter === 'Poor Website'
              ? 'bg-black text-white shadow-xs'
              : 'bg-white text-neutral-700 border border-neutral-200 hover:border-black'
          }`}
        >
          📉 Outdated / Poor Websites
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-xl text-xs font-medium">
          {error}
        </div>
      )}

      {/* Opportunities List Table */}
      <div className="bg-white border border-neutral-200 rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-neutral-200 bg-neutral-50 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-black">
            Found {pagination.totalRecords} Web Prospects
          </span>
          <span className="text-[11px] text-neutral-500 font-mono">
            Direct Outreach Pipeline
          </span>
        </div>

        <div className="overflow-x-auto min-h-[300px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-neutral-950 text-white font-semibold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="p-3">Business Name</th>
                <th className="p-3">Phone</th>
                <th className="p-3">Email</th>
                <th className="p-3">Location</th>
                <th className="p-3">Website Status</th>
                <th className="p-3">Lead Status</th>
                <th className="p-3 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {loading ? (
                <tr>
                  <td colSpan="7" className="p-12 text-center text-neutral-500 font-mono text-xs">
                    Loading opportunities...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="p-12 text-center text-neutral-500 text-xs">
                    No website prospects in this category currently.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.lead_id} className={`transition-colors ${getStatusRowClasses(lead.lead_status)}`}>
                    <td className="p-3 font-bold text-black max-w-[220px]">
                      <button
                        onClick={() => {
                          setActiveLead(lead);
                          setIsModalOpen(true);
                        }}
                        className="hover:underline text-left block truncate"
                      >
                        {lead.business_name}
                      </button>
                      <span className="text-[10px] text-neutral-400 font-mono">
                        {lead.industry || 'Business'} • {lead.lead_id}
                      </span>
                    </td>

                    <td className="p-3 font-mono text-[11px] text-neutral-800">
                      {lead.phone || <span className="text-neutral-400 italic">No Phone</span>}
                    </td>

                    <td className="p-3 font-mono text-[11px] text-neutral-800">
                      {lead.email || <span className="text-neutral-400 italic">No Email</span>}
                    </td>

                    <td className="p-3 text-neutral-700">
                      {lead.city || '—'}, {lead.state || ''}
                    </td>

                    <td className="p-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                          lead.website_status === 'No Website'
                            ? 'bg-black text-white'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {lead.website_status}
                      </span>
                    </td>

                    <td className="p-3">
                      <select
                        value={lead.lead_status}
                        onChange={(e) => handleInlineStatusChange(lead.lead_id, e.target.value)}
                        className={`text-xs font-semibold py-1 px-2 rounded-lg border-0 focus:ring-1 focus:ring-black cursor-pointer ${
                          lead.lead_status === 'Contacted'
                            ? 'bg-emerald-200 text-emerald-900 hover:bg-emerald-300'
                            : lead.lead_status === 'Follow-up'
                            ? 'bg-amber-200 text-amber-900 hover:bg-amber-300'
                            : lead.lead_status === 'Interested'
                            ? 'bg-blue-200 text-blue-900 hover:bg-blue-300'
                            : lead.lead_status === 'Meeting'
                            ? 'bg-violet-200 text-violet-900 hover:bg-violet-300'
                            : lead.lead_status === 'Proposal Sent'
                            ? 'bg-orange-200 text-orange-900 hover:bg-orange-300'
                            : lead.lead_status === 'Converted'
                            ? 'bg-emerald-300 text-emerald-900 hover:bg-emerald-400'
                            : 'bg-neutral-100 text-neutral-900 hover:bg-neutral-200'
                        }`}
                      >
                        <option value="New">New</option>
                        <option value="Contacted">Contacted</option>
                        <option value="Follow-up">Follow-up</option>
                        <option value="Interested">Interested</option>
                        <option value="Meeting">Meeting</option>
                        <option value="Proposal Sent">Proposal Sent</option>
                        <option value="Converted">Converted</option>
                      </select>
                    </td>

                    <td className="p-3 text-right pr-4">
                      <button
                        onClick={() => {
                          setActiveLead(lead);
                          setIsModalOpen(true);
                        }}
                        className="p-1.5 text-neutral-600 hover:text-black hover:bg-neutral-200 rounded-lg transition-colors"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="p-4 border-t border-neutral-200 bg-white flex items-center justify-between text-xs text-neutral-600">
          <div>
            Showing <strong className="font-mono text-black">{leads.length}</strong> of{' '}
            <strong className="font-mono text-black">{pagination.totalRecords}</strong> opportunities
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPagination((p) => ({ ...p, page: Math.max(1, p.page - 1) }))}
              disabled={pagination.page <= 1}
              className="p-1.5 bg-neutral-100 hover:bg-neutral-200 disabled:opacity-40 rounded-lg text-black"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono font-bold text-black px-2">
              Page {pagination.page} / {pagination.totalPages || 1}
            </span>
            <button
              onClick={() => setPagination((p) => ({ ...p, page: Math.min(pagination.totalPages, p.page + 1) }))}
              disabled={pagination.page >= pagination.totalPages}
              className="p-1.5 bg-neutral-100 hover:bg-neutral-200 disabled:opacity-40 rounded-lg text-black"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <LeadModal
        isOpen={isModalOpen}
        lead={activeLead}
        onClose={() => {
          setIsModalOpen(false);
          setActiveLead(null);
        }}
        onSaveSuccess={loadOpportunities}
      />
    </div>
  );
}
