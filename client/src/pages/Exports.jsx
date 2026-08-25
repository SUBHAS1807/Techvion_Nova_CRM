import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Download,
  CheckCircle2,
  FileText,
  Filter,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';
import { getExportUrl } from '../utils/api';

export default function Exports() {
  const [format, setFormat] = useState('excel');
  const [selectedPreset, setSelectedPreset] = useState('all');

  // Custom filter state
  const [customFilters, setCustomFilters] = useState({
    city: '',
    website_status: '',
    lead_status: '',
    data_quality: '',
  });

  const PRESETS = [
    {
      id: 'all',
      title: 'Full Database Export',
      desc: 'All leads currently stored in the CRM with all contact and metadata columns.',
      params: {},
    },
    {
      id: 'no_website',
      title: 'Web Prospecting Export (No Website)',
      desc: 'Targeted export containing only businesses without an active website for web sales.',
      params: { website_status: 'No Website', has_website: 'no' },
    },
    {
      id: 'high_quality',
      title: 'High Data Quality Leads',
      desc: 'Fully enriched and verified leads with valid emails and phone numbers.',
      params: { data_quality: 'High' },
    },
    {
      id: 'contacted_interested',
      title: 'Active Pipeline (Contacted & Interested)',
      desc: 'Leads currently undergoing outreach and discussion.',
      params: { lead_status: 'Interested' },
    },
  ];

  const handleDownload = (params = {}) => {
    const url = getExportUrl(format, params);
    window.open(url, '_blank');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-neutral-200">
        <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
          <FileSpreadsheet className="w-6 h-6 text-black" />
          <span>CRM Export Center</span>
        </h1>
        <p className="text-xs text-neutral-500 mt-1">
          Generate clean RFC 4180 CSV files or genuine Black & White formatted Microsoft Excel (.xlsx) workbooks.
        </p>
      </div>

      {/* Format Selector */}
      <div className="card space-y-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black">
          1. Select Export Format
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div
            onClick={() => setFormat('excel')}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              format === 'excel'
                ? 'border-black bg-neutral-950 text-white shadow-md'
                : 'border-neutral-200 bg-white text-black hover:border-neutral-400'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="font-bold text-sm flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4" />
                <span>Microsoft Excel Workbook (.xlsx)</span>
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white text-black font-bold">
                XLSX
              </span>
            </div>
            <p
              className={`text-xs mt-2 ${
                format === 'excel' ? 'text-neutral-300' : 'text-neutral-500'
              }`}
            >
              Genuine <code>.xlsx</code> with black & white styling, frozen header row, auto-fit columns, and filter handles.
            </p>
          </div>

          <div
            onClick={() => setFormat('csv')}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              format === 'csv'
                ? 'border-black bg-neutral-950 text-white shadow-md'
                : 'border-neutral-200 bg-white text-black hover:border-neutral-400'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="font-bold text-sm flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span>Clean CSV Spreadsheet (.csv)</span>
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white text-black font-bold">
                CSV
              </span>
            </div>
            <p
              className={`text-xs mt-2 ${
                format === 'csv' ? 'text-neutral-300' : 'text-neutral-500'
              }`}
            >
              Technical RFC 4180 UTF-8 CSV without HTML or broken rows. Opens seamlessly in Excel, Google Sheets & LibreOffice.
            </p>
          </div>
        </div>
      </div>

      {/* Preset Segments */}
      <div className="card space-y-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-black">
          2. Quick Export Segments
        </h2>

        <div className="space-y-3">
          {PRESETS.map((preset) => (
            <div
              key={preset.id}
              className="p-4 rounded-xl border border-neutral-200 hover:border-black transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-neutral-50/50"
            >
              <div>
                <h3 className="text-xs font-bold text-black">{preset.title}</h3>
                <p className="text-xs text-neutral-500 mt-0.5">{preset.desc}</p>
              </div>

              <button
                onClick={() => handleDownload(preset.params)}
                className="btn-primary text-xs shrink-0 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download ({format.toUpperCase()})</span>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Re-import Guarantee */}
      <div className="bg-neutral-100 rounded-xl p-5 border border-neutral-200 text-xs space-y-2">
        <div className="font-bold text-black flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-black" />
          <span>Excel Re-Import Compatibility Guarantee</span>
        </div>
        <p className="text-neutral-600">
          Any Excel file exported from TechvionNova CRM can be uploaded right back into the system through the <strong>Import</strong> module. The intelligent column mapper will automatically recognize all standard headers without manual intervention.
        </p>
      </div>
    </div>
  );
}
