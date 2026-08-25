import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  FileCheck,
  Filter,
  ShieldCheck,
  Database,
  ArrowLeft
} from 'lucide-react';
import { previewImportFile, confirmImport } from '../utils/api';

export default function ImportLeads() {
  const navigate = useNavigate();

  // Wizard Steps: 1 (Upload), 2 (Mapping), 3 (Preview & Health Check), 4 (Completed)
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Preview Data from Server
  const [previewData, setPreviewData] = useState(null);
  const [columnMapping, setColumnMapping] = useState({});
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [defaultSource, setDefaultSource] = useState('Excel Import');

  // Import Result
  const [importResult, setImportResult] = useState(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (uploadedFile) => {
    setFile(uploadedFile);
    setLoading(true);
    setError('');

    try {
      const res = await previewImportFile(uploadedFile);
      if (res.success) {
        setPreviewData(res);
        setColumnMapping(res.columnMapping || {});
        setStep(2);
      }
    } catch (err) {
      setError(err.message || 'Failed to read file for preview');
    } finally {
      setLoading(false);
    }
  };

  const handleMappingChange = (header, targetField) => {
    setColumnMapping((prev) => ({
      ...prev,
      [header]: targetField,
    }));
  };

  const handleConfirmImport = async () => {
    setLoading(true);
    setError('');

    try {
      const payload = {
        rawRows: previewData.rawRows,
        columnMapping,
        skipDuplicates,
        defaultSource,
      };

      const res = await confirmImport(payload);
      if (res.success) {
        setImportResult(res);
        setStep(4);
        window.dispatchEvent(new CustomEvent('refresh-leads'));
      }
    } catch (err) {
      setError(err.message || 'Failed to import clean data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-4 border-b border-neutral-200">
        <h1 className="text-2xl font-bold tracking-tight text-black flex items-center gap-2">
          <span>Excel / CSV Lead Importer</span>
        </h1>
        <p className="text-xs text-neutral-500 mt-1">
          Upload spreadsheets, automatically detect & map columns, validate location consistency, and import cleaned data.
        </p>
      </div>

      {/* Wizard Progress Bar */}
      <div className="grid grid-cols-4 gap-2 text-xs font-semibold">
        <div
          className={`py-2 px-3 rounded-lg border text-center transition-all ${
            step === 1
              ? 'bg-black text-white border-black shadow-xs'
              : step > 1
              ? 'bg-neutral-100 text-neutral-800 border-neutral-300'
              : 'bg-white text-neutral-400 border-neutral-200'
          }`}
        >
          1. Upload File
        </div>
        <div
          className={`py-2 px-3 rounded-lg border text-center transition-all ${
            step === 2
              ? 'bg-black text-white border-black shadow-xs'
              : step > 2
              ? 'bg-neutral-100 text-neutral-800 border-neutral-300'
              : 'bg-white text-neutral-400 border-neutral-200'
          }`}
        >
          2. Column Mapping
        </div>
        <div
          className={`py-2 px-3 rounded-lg border text-center transition-all ${
            step === 3
              ? 'bg-black text-white border-black shadow-xs'
              : step > 3
              ? 'bg-neutral-100 text-neutral-800 border-neutral-300'
              : 'bg-white text-neutral-400 border-neutral-200'
          }`}
        >
          3. Preview & Validate
        </div>
        <div
          className={`py-2 px-3 rounded-lg border text-center transition-all ${
            step === 4
              ? 'bg-black text-white border-black shadow-xs'
              : 'bg-white text-neutral-400 border-neutral-200'
          }`}
        >
          4. Complete
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 p-4 rounded-xl text-xs font-medium">
          {error}
        </div>
      )}

      {/* STEP 1: Upload File */}
      {step === 1 && (
        <div className="space-y-6">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            className="border-2 border-dashed border-neutral-300 hover:border-black rounded-2xl p-12 text-center bg-white transition-all cursor-pointer group"
            onClick={() => document.getElementById('file-upload-input').click()}
          >
            <input
              id="file-upload-input"
              type="file"
              accept=".xlsx, .xls, .csv"
              onChange={handleFileInput}
              className="hidden"
            />
            <div className="w-16 h-16 bg-neutral-100 group-hover:bg-black group-hover:text-white text-neutral-700 rounded-2xl flex items-center justify-center mx-auto transition-colors shadow-xs">
              <UploadCloud className="w-8 h-8" />
            </div>

            <h3 className="mt-4 text-base font-bold text-black">
              Click to upload or drag and drop spreadsheet
            </h3>
            <p className="text-xs text-neutral-500 mt-1 font-mono">
              Supports Microsoft Excel (.xlsx, .xls) and CSV (.csv) files up to 25MB
            </p>

            <div className="mt-6 inline-flex items-center gap-2 bg-neutral-100 text-neutral-700 text-xs font-semibold px-4 py-2 rounded-lg border border-neutral-200">
              <FileSpreadsheet className="w-4 h-4" />
              <span>Select Lead File from Computer</span>
            </div>
          </div>

          {/* Cleaning Guarantee */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card text-xs">
              <div className="font-bold text-black flex items-center gap-1.5 mb-1">
                <CheckCircle2 className="w-4 h-4 text-black" />
                <span>Auto-Clean Artifacts</span>
              </div>
              <p className="text-neutral-500">
                Automatically strips <code>undefined</code>, <code>null</code>, <code>NaN</code>, <code>[object Object]</code>, and malformed characters.
              </p>
            </div>

            <div className="card text-xs">
              <div className="font-bold text-black flex items-center gap-1.5 mb-1">
                <AlertTriangle className="w-4 h-4 text-black" />
                <span>Location Validation</span>
              </div>
              <p className="text-neutral-500">
                Detects mismatched cities and states (e.g. Kolkata in Telangana) and marks them for verification.
              </p>
            </div>

            <div className="card text-xs">
              <div className="font-bold text-black flex items-center gap-1.5 mb-1">
                <ShieldCheck className="w-4 h-4 text-black" />
                <span>Duplicate Guard</span>
              </div>
              <p className="text-neutral-500">
                Prevents duplicate records by cross-referencing email, phone, website, and business name.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: Column Mapping */}
      {step === 2 && previewData && (
        <div className="card space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
            <div>
              <h2 className="text-base font-bold text-black">
                Intelligent Column Detection & Mapping
              </h2>
              <p className="text-xs text-neutral-500">
                File: <strong className="font-mono text-black">{previewData.filename}</strong> ({previewData.summary.totalRows} rows found)
              </p>
            </div>
            <button
              onClick={() => setStep(1)}
              className="btn-ghost text-xs flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Change File</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[450px] overflow-y-auto pr-2">
            {previewData.headers.map((header) => {
              const currentMapped = columnMapping[header] || 'ignore';
              return (
                <div
                  key={header}
                  className="p-3.5 rounded-xl border border-neutral-200 bg-neutral-50 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] text-neutral-400 font-mono uppercase tracking-wider block">
                      Spreadsheet Column
                    </span>
                    <span className="text-xs font-bold text-black truncate block font-mono">
                      "{header}"
                    </span>
                  </div>

                  <ArrowRight className="w-4 h-4 text-neutral-400 shrink-0" />

                  <div className="w-48">
                    <span className="text-[10px] text-neutral-400 font-mono uppercase tracking-wider block">
                      CRM Field
                    </span>
                    <select
                      value={currentMapped}
                      onChange={(e) => handleMappingChange(header, e.target.value)}
                      className={`select-field text-xs py-1 ${
                        currentMapped !== 'ignore' ? 'font-bold text-black border-black' : 'text-neutral-500'
                      }`}
                    >
                      <option value="ignore">— Ignore Column —</option>
                      {previewData.standardFields?.map((f) => (
                        <option key={f.key} value={f.key}>
                          {f.label} {f.required ? '*' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-4 border-t border-neutral-200 flex justify-between items-center">
            <button onClick={() => setStep(1)} className="btn-secondary text-xs">
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <span>Continue to Pre-Import Preview</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Preview & Health Audit */}
      {step === 3 && previewData && (
        <div className="space-y-6">
          {/* Health Audit Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="card text-center p-3">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block font-semibold">
                Total Rows
              </span>
              <span className="text-xl font-extrabold font-mono text-black">
                {previewData.summary.totalRows}
              </span>
            </div>

            <div className="card text-center p-3">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block font-semibold">
                Valid Records
              </span>
              <span className="text-xl font-extrabold font-mono text-black">
                {previewData.summary.validRecords}
              </span>
            </div>

            <div className="card text-center p-3">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block font-semibold">
                Duplicates
              </span>
              <span className="text-xl font-extrabold font-mono text-black">
                {previewData.summary.duplicateRecords}
              </span>
            </div>

            <div className="card text-center p-3">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block font-semibold">
                Missing Email
              </span>
              <span className="text-xl font-extrabold font-mono text-neutral-700">
                {previewData.summary.missingEmail}
              </span>
            </div>

            <div className="card text-center p-3">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider block font-semibold">
                Missing Web
              </span>
              <span className="text-xl font-extrabold font-mono text-neutral-700">
                {previewData.summary.missingWebsite}
              </span>
            </div>

            <div className="card text-center p-3 border-amber-300 bg-amber-50/50">
              <span className="text-[10px] text-amber-800 uppercase tracking-wider block font-semibold">
                Needs Verify
              </span>
              <span className="text-xl font-extrabold font-mono text-amber-900">
                {previewData.summary.needsVerification}
              </span>
            </div>
          </div>

          {/* Import Options Box */}
          <div className="card space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-black">
              Import Configuration
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={skipDuplicates}
                  onChange={(e) => setSkipDuplicates(e.target.checked)}
                  className="w-4 h-4 text-black focus:ring-black border-neutral-300 rounded"
                />
                <span className="text-neutral-800">
                  <strong>Skip Duplicates</strong> (Do not import if email, phone, or business matches)
                </span>
              </label>

              <div className="flex items-center gap-2">
                <span className="text-neutral-600 font-medium">Default Source:</span>
                <input
                  type="text"
                  value={defaultSource}
                  onChange={(e) => setDefaultSource(e.target.value)}
                  className="input-field text-xs py-1"
                />
              </div>
            </div>
          </div>

          {/* Sample Cleaned Rows Table */}
          <div className="bg-white border border-neutral-200 rounded-xl shadow-xs overflow-hidden">
            <div className="p-4 border-b border-neutral-200 bg-neutral-50 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-black">
                Cleaned Data Sample Preview ({previewData.sampleRows?.length} rows)
              </h3>
              <span className="text-[11px] text-neutral-500 font-mono">
                Cleaned according to CRM schema
              </span>
            </div>

            <div className="overflow-x-auto max-h-[350px]">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-neutral-950 text-white font-semibold uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="p-2.5">Row</th>
                    <th className="p-2.5">Business Name</th>
                    <th className="p-2.5">Email</th>
                    <th className="p-2.5">Phone</th>
                    <th className="p-2.5">Website</th>
                    <th className="p-2.5">Location</th>
                    <th className="p-2.5">Quality</th>
                    <th className="p-2.5">Status Flag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 font-mono text-[11px]">
                  {previewData.sampleRows?.map((row, idx) => (
                    <tr
                      key={idx}
                      className={`hover:bg-neutral-50 ${
                        row.is_duplicate ? 'bg-amber-50/50' : ''
                      }`}
                    >
                      <td className="p-2.5 text-neutral-400">#{row.row_index}</td>
                      <td className="p-2.5 font-bold text-black">{row.business_name}</td>
                      <td className="p-2.5 text-neutral-600">{row.email || '—'}</td>
                      <td className="p-2.5 text-neutral-600">{row.phone || '—'}</td>
                      <td className="p-2.5 text-neutral-600">{row.website || 'No Website'}</td>
                      <td className="p-2.5 text-neutral-600">
                        {row.city || '—'}, {row.state || ''}
                      </td>
                      <td className="p-2.5 font-bold">{row.data_quality}</td>
                      <td className="p-2.5">
                        {row.is_duplicate ? (
                          <span className="badge badge-warning text-[9px]">Duplicate</span>
                        ) : row.needs_verification ? (
                          <span className="badge badge-warning text-[9px]">⚠️ Verify Location</span>
                        ) : (
                          <span className="badge badge-black text-[9px]">Clean</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Final Action Controls */}
          <div className="pt-4 flex justify-between items-center">
            <button onClick={() => setStep(2)} className="btn-secondary text-xs">
              Back to Mapping
            </button>
            <button
              onClick={handleConfirmImport}
              disabled={loading}
              className="btn-primary text-xs py-2.5 px-6 flex items-center gap-2"
            >
              <FileCheck className="w-4 h-4" />
              <span>{loading ? 'Importing Clean Leads...' : 'Import Clean Data to CRM'}</span>
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: Completion */}
      {step === 4 && importResult && (
        <div className="card text-center p-12 space-y-6">
          <div className="w-16 h-16 bg-black text-white rounded-2xl flex items-center justify-center mx-auto shadow-md">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-black tracking-tight">
              Import Completed Successfully!
            </h2>
            <p className="text-xs text-neutral-500 max-w-md mx-auto">
              {importResult.message}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4 max-w-lg mx-auto text-xs font-mono">
            <div className="p-3 bg-neutral-100 rounded-xl border border-neutral-200">
              <span className="text-[10px] text-neutral-500 uppercase block">Imported</span>
              <span className="text-xl font-bold text-black">{importResult.importedCount}</span>
            </div>
            <div className="p-3 bg-neutral-100 rounded-xl border border-neutral-200">
              <span className="text-[10px] text-neutral-500 uppercase block">Skipped Duplicates</span>
              <span className="text-xl font-bold text-neutral-700">{importResult.skippedDuplicates}</span>
            </div>
            <div className="p-3 bg-neutral-100 rounded-xl border border-neutral-200">
              <span className="text-[10px] text-neutral-500 uppercase block">Invalid Skipped</span>
              <span className="text-xl font-bold text-neutral-700">{importResult.skippedInvalid}</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 pt-4">
            <button
              onClick={() => {
                setStep(1);
                setFile(null);
                setPreviewData(null);
              }}
              className="btn-secondary text-xs"
            >
              Import Another File
            </button>
            <button
              onClick={() => navigate('/leads')}
              className="btn-primary text-xs"
            >
              View Leads in CRM Table →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
