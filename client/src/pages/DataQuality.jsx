import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Edit2,
  RefreshCw,
  Sparkles,
  MapPin,
  Mail,
  Search
} from 'lucide-react';
import { fetchLeads, updateLead } from '../utils/api';
import LeadModal from '../components/LeadModal';

export default function DataQuality() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewTab, setViewTab] = useState('needs_verification'); // 'needs_verification' | 'low_quality' | 'all'

  const [activeLead, setActiveLead] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError('');

    try {
      const params = {
        limit: 100,
        needs_verification: viewTab === 'needs_verification' ? 'true' : '',
        data_quality: viewTab === 'low_quality' ? 'Low' : '',
      };

      const res = await fetchLeads(params);
      if (res.success) {
        setLeads(res.data);
      }
    } catch (err) {
      setError(err.message || 'Failed to load data quality records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [viewTab]);

  const handleVerify = async (leadId) => {
    try {
      await updateLead(leadId, { is_verified: true, needs_verification: false, verification_reason: '' });
      setLeads((prev) => prev.filter((l) => l.lead_id !== leadId));
      window.dispatchEvent(new CustomEvent('refresh-leads'));
    } catch (err) {
      alert('Failed to verify lead: ' + err.message);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-black" />
            <span>Data Quality & Location Verification</span>
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Resolve geographic anomalies (e.g. Kolkata marked in Telangana), risky emails, and incomplete records.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setViewTab('needs_verification')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            viewTab === 'needs_verification'
              ? 'bg-black text-white shadow-xs'
              : 'bg-white text-neutral-700 border border-neutral-200 hover:border-black'
          }`}
        >
          ⚠️ Location & Data Conflicts
        </button>

        <button
          onClick={() => setViewTab('low_quality')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
            viewTab === 'low_quality'
              ? 'bg-black text-white shadow-xs'
              : 'bg-white text-neutral-700 border border-neutral-200 hover:border-black'
          }`}
        >
          📉 Low Completeness Records
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-xl text-xs font-medium">
          {error}
        </div>
      )}

      {/* Leads Table */}
      <div className="bg-white border border-neutral-200 rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-neutral-200 bg-neutral-50 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-black">
            Found {leads.length} Records Requiring Attention
          </span>
        </div>

        <div className="overflow-x-auto min-h-[300px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-neutral-950 text-white font-semibold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="p-3">Business Name</th>
                <th className="p-3">Detected Issue / Reason</th>
                <th className="p-3">Current Location</th>
                <th className="p-3">Email & Status</th>
                <th className="p-3">Data Quality</th>
                <th className="p-3 text-right pr-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {loading ? (
                <tr>
                  <td colSpan="6" className="p-12 text-center text-neutral-500 font-mono text-xs">
                    Scanning records...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="6" className="p-12 text-center text-neutral-500 text-xs">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <CheckCircle2 className="w-8 h-8 text-black" />
                      <span className="font-bold text-black text-sm">All Records Clean & Verified!</span>
                      <span className="text-neutral-500">No anomalies or conflicts detected in the CRM.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.lead_id} className="hover:bg-neutral-50 transition-colors">
                    <td className="p-3 font-bold text-black max-w-[200px]">
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
                        {lead.lead_id}
                      </span>
                    </td>

                    <td className="p-3 max-w-[280px]">
                      <div className="flex items-start gap-1.5 text-amber-900 bg-amber-50 p-2 rounded-lg border border-amber-200 text-[11px]">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0 mt-0.5" />
                        <span>{lead.verification_reason || 'Flagged for verification check.'}</span>
                      </div>
                    </td>

                    <td className="p-3 text-neutral-800">
                      <strong>{lead.city || 'No City'}</strong>, {lead.state || 'No State'}
                      <div className="text-[10px] text-neutral-400 font-mono">{lead.country || 'India'}</div>
                    </td>

                    <td className="p-3 font-mono text-[11px]">
                      {lead.email || <span className="text-neutral-400 italic">Missing</span>}
                      <div>
                        <span className="badge badge-gray text-[9px] mt-0.5">{lead.email_status}</span>
                      </div>
                    </td>

                    <td className="p-3">
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

                    <td className="p-3 text-right pr-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleVerify(lead.lead_id)}
                          className="px-2.5 py-1 bg-black text-white text-xs font-semibold rounded-lg hover:bg-neutral-800 transition-colors"
                        >
                          Mark Clean
                        </button>
                        <button
                          onClick={() => {
                            setActiveLead(lead);
                            setIsModalOpen(true);
                          }}
                          className="p-1.5 text-neutral-600 hover:text-black hover:bg-neutral-200 rounded-lg transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <LeadModal
        isOpen={isModalOpen}
        lead={activeLead}
        onClose={() => {
          setIsModalOpen(false);
          setActiveLead(null);
        }}
        onSaveSuccess={loadData}
      />
    </div>
  );
}
