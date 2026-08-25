import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  MailCheck,
  Globe,
  Globe2,
  CheckCircle2,
  AlertTriangle,
  PhoneCall,
  Flame,
  Award,
  ArrowUpRight,
  UploadCloud,
  FileSpreadsheet,
  ShieldCheck,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { fetchStats } from '../utils/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [statsData, setStatsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStats = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchStats();
      if (res.success) {
        setStatsData(res);
      }
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    const handleRefresh = () => loadStats();
    window.addEventListener('refresh-leads', handleRefresh);
    window.addEventListener('lead-updated', handleRefresh);
    return () => {
      window.removeEventListener('refresh-leads', handleRefresh);
      window.removeEventListener('lead-updated', handleRefresh);
    };
  }, []);

  const stats = statsData?.stats || {
    totalLeads: 0,
    validEmails: 0,
    leadsWithoutWebsite: 0,
    leadsWithWebsite: 0,
    verifiedLeads: 0,
    leadsNeedingVerification: 0,
    contacted: 0,
    interested: 0,
    converted: 0,
  };

  // Black & White CRM KPI Cards
  const KPI_CARDS = [
    {
      title: 'Total Leads',
      value: stats.totalLeads,
      icon: Users,
      desc: 'All leads in CRM database',
      onClick: () => navigate('/leads'),
      highlight: false,
    },
    {
      title: 'Valid Emails',
      value: stats.validEmails,
      icon: MailCheck,
      desc: 'Verified email addresses',
      onClick: () => navigate('/leads?email_status=Valid'),
      highlight: false,
    },
    {
      title: 'Leads Without Website',
      value: stats.leadsWithoutWebsite,
      icon: Globe2,
      desc: 'Prime website sales opportunities',
      onClick: () => navigate('/website-opportunities'),
      highlight: true,
    },
    {
      title: 'Leads With Website',
      value: stats.leadsWithWebsite,
      icon: Globe,
      desc: 'Existing web presence identified',
      onClick: () => navigate('/leads?has_website=yes'),
      highlight: false,
    },
    {
      title: 'Verified Leads',
      value: stats.verifiedLeads,
      icon: CheckCircle2,
      desc: 'Manually/system verified leads',
      onClick: () => navigate('/leads?is_verified=true'),
      highlight: false,
    },
    {
      title: 'Needs Verification',
      value: stats.leadsNeedingVerification,
      icon: AlertTriangle,
      desc: 'Location or data conflict flagged',
      onClick: () => navigate('/data-quality'),
      warning: stats.leadsNeedingVerification > 0,
    },
    {
      title: 'Contacted',
      value: stats.contacted,
      icon: PhoneCall,
      desc: 'Outreach started',
      onClick: () => navigate('/leads?lead_status=Contacted'),
      highlight: false,
    },
    {
      title: 'Interested',
      value: stats.interested,
      icon: Flame,
      desc: 'Positive response received',
      onClick: () => navigate('/leads?lead_status=Interested'),
      highlight: false,
    },
    {
      title: 'Converted',
      value: stats.converted,
      icon: Award,
      desc: 'Successfully closed deals',
      onClick: () => navigate('/leads?lead_status=Converted'),
      highlight: false,
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-neutral-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-black">
            Lead CRM Dashboard
          </h1>
          <p className="text-xs text-neutral-500 mt-1">
            Overview of prospect collection, data hygiene, verification status, and conversion pipeline.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/import')}
            className="btn-primary text-xs"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Import Excel / CSV</span>
          </button>
          <button
            onClick={() => navigate('/exports')}
            className="btn-secondary text-xs"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span>Export Data</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 px-4 py-3 rounded-lg text-xs font-medium">
          {error}
        </div>
      )}

      {/* 9 KPI Black & White Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {KPI_CARDS.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              onClick={card.onClick}
              className={`p-5 rounded-xl border transition-all cursor-pointer group select-none ${
                card.highlight
                  ? 'bg-black text-white border-black shadow-md hover:bg-neutral-900'
                  : card.warning
                  ? 'bg-white text-black border-amber-300 hover:border-amber-500 shadow-xs'
                  : 'bg-white text-black border-neutral-200 hover:border-black shadow-xs'
              }`}
            >
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs font-semibold uppercase tracking-wider ${
                    card.highlight ? 'text-neutral-300' : 'text-neutral-500'
                  }`}
                >
                  {card.title}
                </span>
                <div
                  className={`p-2 rounded-lg ${
                    card.highlight
                      ? 'bg-neutral-800 text-white'
                      : card.warning
                      ? 'bg-amber-100 text-amber-900'
                      : 'bg-neutral-100 text-black group-hover:bg-black group-hover:text-white transition-colors'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
              </div>

              <div className="mt-4 flex items-baseline justify-between">
                <span className="text-3xl font-extrabold tracking-tight font-mono">
                  {loading ? '—' : card.value.toLocaleString()}
                </span>
                <ArrowUpRight
                  className={`w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 ${
                    card.highlight ? 'text-neutral-400' : 'text-neutral-400 group-hover:text-black'
                  }`}
                />
              </div>

              <p
                className={`mt-1.5 text-xs ${
                  card.highlight ? 'text-neutral-400' : 'text-neutral-500'
                }`}
              >
                {card.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Quick Action Shortcuts & Health Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Leads */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-black">
                Recent Leads
              </h2>
              <p className="text-xs text-neutral-500">Latest business prospects added to CRM</p>
            </div>
            <button
              onClick={() => navigate('/leads')}
              className="text-xs text-black font-semibold hover:underline flex items-center gap-1"
            >
              <span>View All Leads</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-neutral-100 overflow-x-auto">
            {loading ? (
              <div className="py-8 text-center text-xs text-neutral-400 font-mono">
                Loading recent leads...
              </div>
            ) : !statsData?.recentLeads || statsData.recentLeads.length === 0 ? (
              <div className="py-8 text-center text-xs text-neutral-500">
                No leads recorded yet. Click "Import Excel / CSV" to begin.
              </div>
            ) : (
              statsData.recentLeads.map((lead) => (
                <div
                  key={lead.lead_id}
                  onClick={() => navigate(`/leads?search=${encodeURIComponent(lead.business_name)}`)}
                  className="py-3 px-2 flex items-center justify-between hover:bg-neutral-50 rounded-lg cursor-pointer transition-colors"
                >
                  <div className="min-w-0 pr-4">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-bold text-black truncate">
                        {lead.business_name}
                      </p>
                      {lead.needs_verification ? (
                        <span className="badge badge-warning text-[10px]">⚠️ Verify</span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-[11px] text-neutral-500 font-mono">
                      <span>{lead.city || 'No City'}</span>
                      <span>•</span>
                      <span>{lead.industry || 'General'}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                        lead.website_status === 'No Website'
                          ? 'bg-neutral-900 text-white font-mono'
                          : 'bg-neutral-100 text-neutral-700'
                      }`}
                    >
                      {lead.website_status}
                    </span>
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                        lead.lead_status === 'Contacted'
                          ? 'bg-emerald-200 text-emerald-900'
                          : lead.lead_status === 'Follow-up'
                          ? 'bg-amber-200 text-amber-900'
                          : lead.lead_status === 'Interested'
                          ? 'bg-blue-200 text-blue-900'
                          : lead.lead_status === 'Meeting'
                          ? 'bg-violet-200 text-violet-900'
                          : lead.lead_status === 'Proposal Sent'
                          ? 'bg-orange-200 text-orange-900'
                          : lead.lead_status === 'Converted'
                          ? 'bg-emerald-300 text-emerald-900'
                          : lead.lead_status === 'Not Interested'
                          ? 'bg-red-100 text-red-800'
                          : lead.lead_status === 'Closed'
                          ? 'bg-neutral-200 text-neutral-800'
                          : 'bg-neutral-200 text-neutral-800'
                      }`}
                    >
                      {lead.lead_status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 1 Col: Data Health & Opportunities */}
        <div className="space-y-6">
          {/* Web Prospecting Target */}
          <div className="bg-neutral-950 text-white rounded-xl p-5 border border-black shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold text-neutral-400 uppercase tracking-widest">
              <Globe2 className="w-4 h-4 text-white" />
              <span>Web Development Leads</span>
            </div>
            <div className="mt-3">
              <p className="text-3xl font-extrabold font-mono text-white">
                {stats.leadsWithoutWebsite}
              </p>
              <p className="text-xs text-neutral-400 mt-1">
                Businesses identified with <strong>No Website</strong> ready for website development outreach.
              </p>
            </div>
            <button
              onClick={() => navigate('/website-opportunities')}
              className="mt-4 w-full py-2 bg-white text-black text-xs font-bold rounded-lg hover:bg-neutral-200 transition-colors"
            >
              Open Web Opportunities →
            </button>
          </div>

          {/* Data Quality Health Box */}
          <div className="card">
            <h3 className="text-xs font-bold uppercase tracking-wider text-black mb-3">
              Data Quality Breakdown
            </h3>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-600 font-medium">High Quality</span>
                <span className="font-mono font-bold text-black">
                  {statsData?.qualityBreakdown?.High || 0}
                </span>
              </div>
              <div className="w-full bg-neutral-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-black h-1.5 rounded-full"
                  style={{
                    width: `${
                      stats.totalLeads > 0
                        ? ((statsData?.qualityBreakdown?.High || 0) / stats.totalLeads) * 100
                        : 0
                    }%`,
                  }}
                ></div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-neutral-600 font-medium">Medium Quality</span>
                <span className="font-mono font-bold text-neutral-700">
                  {statsData?.qualityBreakdown?.Medium || 0}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-neutral-600 font-medium">Low Quality</span>
                <span className="font-mono font-bold text-neutral-700">
                  {statsData?.qualityBreakdown?.Low || 0}
                </span>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-neutral-200 flex justify-between items-center">
              <span className="text-xs text-neutral-500">Conflicts Detected</span>
              <span
                className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                  stats.leadsNeedingVerification > 0
                    ? 'bg-amber-100 text-amber-900'
                    : 'bg-neutral-100 text-neutral-700'
                }`}
              >
                {stats.leadsNeedingVerification} records
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
