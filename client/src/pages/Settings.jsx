import React from 'react';
import {
  Settings as SettingsIcon,
  Database,
  CheckCircle2,
  Cpu,
  Layers,
  FileSpreadsheet,
  ShieldCheck
} from 'lucide-react';

export default function Settings() {
  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-neutral-200">
        <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-black" />
          <span>CRM Configuration & Diagnostics</span>
        </h1>
        <p className="text-xs text-neutral-500 mt-1">
          System architecture, database health, automated validation rules, and schema specifications.
        </p>
      </div>

      {/* System Status Card */}
      <div className="card space-y-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black">
          System Diagnostics & Engine Architecture
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="p-4 bg-neutral-50 rounded-xl border border-neutral-200">
            <span className="text-neutral-500 block text-[10px] uppercase font-mono">
              Backend Server
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="font-bold text-black text-sm">Node.js / Express</span>
            </div>
            <p className="text-neutral-400 mt-1 text-[11px]">Strictly JavaScript/TypeScript runtime (No PHP)</p>
          </div>

          <div className="p-4 bg-neutral-50 rounded-xl border border-neutral-200">
            <span className="text-neutral-500 block text-[10px] uppercase font-mono">
              Database Engine
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 rounded-full bg-black"></span>
              <span className="font-bold text-black text-sm">SQL Engine (Dual-Mode)</span>
            </div>
            <p className="text-neutral-400 mt-1 text-[11px]">Indexed SQL storage with WAL journaling</p>
          </div>

          <div className="p-4 bg-neutral-50 rounded-xl border border-neutral-200">
            <span className="text-neutral-500 block text-[10px] uppercase font-mono">
              Frontend Client
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 rounded-full bg-black"></span>
              <span className="font-bold text-black text-sm">React 18 + Tailwind</span>
            </div>
            <p className="text-neutral-400 mt-1 text-[11px]">Pure Black & White high-contrast UI</p>
          </div>
        </div>
      </div>

      {/* Schema & Standard Fields */}
      <div className="card space-y-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black">
          Automated CRM Column Standards
        </h2>
        <p className="text-xs text-neutral-600">
          The following standard CRM fields are auto-detected and normalized during Excel/CSV imports:
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 text-xs font-mono">
          <div className="p-2 bg-neutral-100 rounded-lg text-black font-semibold">business_name *</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">email</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">phone</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">website</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">website_status</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">city</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">state</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">country</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">industry</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">lead_status</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">lead_source</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">contact_person</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">data_quality</div>
          <div className="p-2 bg-neutral-100 rounded-lg text-neutral-800">notes</div>
        </div>
      </div>

      {/* Location Validation Rules */}
      <div className="card space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-black" />
          <span>Location Verification System</span>
        </h2>
        <p className="text-xs text-neutral-600">
          The validation engine detects inconsistencies like <em>Kolkata</em> placed in <em>Telangana</em> or <em>Mumbai</em> in <em>Karnataka</em>. Discrepancies are flagged with <code>⚠️ Needs Verification</code> in the Leads table and isolated in the Data Quality center.
        </p>
      </div>
    </div>
  );
}
