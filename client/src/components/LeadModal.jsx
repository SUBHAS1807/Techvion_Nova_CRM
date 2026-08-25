import React, { useState, useEffect } from 'react';
import {
  X,
  Building2,
  Mail,
  Phone,
  Globe,
  MapPin,
  Tag,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Save,
  Clock,
  Sparkles,
  UserCheck
} from 'lucide-react';
import { createLead, updateLead, deleteLead } from '../utils/api';

const LEAD_STATUSES = [
  'New',
  'Verified',
  'Contacted',
  'Follow-up',
  'Interested',
  'Meeting',
  'Proposal Sent',
  'Converted',
  'Not Interested',
  'Closed',
];

const WEBSITE_STATUSES = [
  'No Website',
  'Working',
  'Broken',
  'Redirect',
  'Poor Website',
  'Under Construction',
  'Unknown',
  'Needs Verification',
];

const EMAIL_STATUSES = ['Valid', 'Invalid', 'Missing', 'Risky', 'Not Verified'];

const LEAD_SOURCES = [
  'Google Maps',
  'Google Search',
  'Website',
  'Facebook',
  'Instagram',
  'LinkedIn',
  'Manual',
  'CSV Import',
  'Excel Import',
  'Other',
];

export default function LeadModal({ isOpen, lead, onClose, onSaveSuccess, onDeleteSuccess }) {
  const [formData, setFormData] = useState({
    business_name: '',
    industry: '',
    email: '',
    email_status: 'Not Verified',
    phone: '',
    website: '',
    website_status: 'Unknown',
    address: '',
    city: '',
    state: '',
    country: '',
    postal_code: '',
    lead_status: 'New',
    lead_source: 'Manual',
    contact_person: '',
    notes: '',
    is_verified: false,
    needs_verification: false,
    verification_reason: '',
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('business');

  const isEditMode = Boolean(lead && lead.lead_id);

  useEffect(() => {
    if (lead) {
      setFormData({
        business_name: lead.business_name || '',
        industry: lead.industry || '',
        email: lead.email || '',
        email_status: lead.email_status || 'Not Verified',
        phone: lead.phone || '',
        website: lead.website || '',
        website_status: lead.website_status || 'Unknown',
        address: lead.address || '',
        city: lead.city || '',
        state: lead.state || '',
        country: lead.country || '',
        postal_code: lead.postal_code || '',
        lead_status: lead.lead_status || 'New',
        lead_source: lead.lead_source || 'Manual',
        contact_person: lead.contact_person || '',
        notes: lead.notes || '',
        is_verified: Boolean(lead.is_verified),
        needs_verification: Boolean(lead.needs_verification),
        verification_reason: lead.verification_reason || '',
      });
    } else {
      setFormData({
        business_name: '',
        industry: '',
        email: '',
        email_status: 'Not Verified',
        phone: '',
        website: '',
        website_status: 'Unknown',
        address: '',
        city: '',
        state: '',
        country: '',
        postal_code: '',
        lead_status: 'New',
        lead_source: 'Manual',
        contact_person: '',
        notes: '',
        is_verified: false,
        needs_verification: false,
        verification_reason: '',
      });
    }
    setError('');
    setActiveTab('business');
  }, [lead, isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.business_name.trim()) {
      setError('Business Name is required');
      return;
    }

    setSaving(true);
    setError('');

    try {
      if (isEditMode) {
        const res = await updateLead(lead.lead_id, formData);
        onSaveSuccess(res.data, 'updated');
      } else {
        const res = await createLead(formData);
        onSaveSuccess(res.data, 'created');
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save lead');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete lead "${formData.business_name}"?`)) {
      return;
    }

    setSaving(true);
    try {
      await deleteLead(lead.lead_id);
      if (onDeleteSuccess) onDeleteSuccess(lead.lead_id);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to delete lead');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs overflow-y-auto">
      <div className="bg-white rounded-2xl border border-neutral-300 w-full max-w-3xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 bg-neutral-950 text-white">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold text-sm">
              {isEditMode ? 'ID' : '+'}
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">
                {isEditMode ? formData.business_name || 'Edit Lead' : 'Create New Lead'}
              </h2>
              {isEditMode && (
                <div className="flex items-center gap-2 mt-0.5 text-xs text-neutral-400 font-mono">
                  <span>{lead.lead_id}</span>
                  <span>•</span>
                  <span>Quality: {lead.data_quality || 'N/A'}</span>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Verification Warning Alert */}
        {formData.needs_verification && (
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-start gap-3 text-amber-900 text-xs">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold">⚠️ Needs Verification: </span>
              <span>{formData.verification_reason || 'Location or data discrepancy detected. Please verify details.'}</span>
            </div>
            <button
              type="button"
              onClick={() =>
                setFormData((prev) => ({
                  ...prev,
                  needs_verification: false,
                  is_verified: true,
                  verification_reason: '',
                }))
              }
              className="text-xs bg-amber-200 hover:bg-amber-300 px-2 py-0.5 rounded font-semibold text-amber-950"
            >
              Mark Verified
            </button>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-neutral-200 bg-neutral-50 px-6 gap-2 text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveTab('business')}
            className={`py-3 px-3 border-b-2 transition-colors ${
              activeTab === 'business'
                ? 'border-black text-black font-semibold'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            Business & Contact
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('location')}
            className={`py-3 px-3 border-b-2 transition-colors ${
              activeTab === 'location'
                ? 'border-black text-black font-semibold'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            Location & Address
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('crm')}
            className={`py-3 px-3 border-b-2 transition-colors ${
              activeTab === 'crm'
                ? 'border-black text-black font-semibold'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            Status & Source
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('notes')}
            className={`py-3 px-3 border-b-2 transition-colors ${
              activeTab === 'notes'
                ? 'border-black text-black font-semibold'
                : 'border-transparent text-neutral-500 hover:text-black'
            }`}
          >
            Notes & Remarks
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[65vh] overflow-y-auto">
          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 px-4 py-2.5 rounded-lg text-xs font-medium">
              {error}
            </div>
          )}

          {/* TAB 1: Business & Contact */}
          {activeTab === 'business' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Business Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="business_name"
                    value={formData.business_name}
                    onChange={handleChange}
                    placeholder="e.g. Roastery Coffee House"
                    required
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Industry / Category
                  </label>
                  <input
                    type="text"
                    name="industry"
                    value={formData.industry}
                    onChange={handleChange}
                    placeholder="e.g. Cafe, Dental Clinic, Legal"
                    className="input-field"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Website URL
                  </label>
                  <input
                    type="text"
                    name="website"
                    value={formData.website}
                    onChange={handleChange}
                    placeholder="e.g. https://example.com or leave blank"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Website Status
                  </label>
                  <select
                    name="website_status"
                    value={formData.website_status}
                    onChange={handleChange}
                    className="select-field"
                  >
                    {WEBSITE_STATUSES.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="e.g. contact@business.com"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Email Status
                  </label>
                  <select
                    name="email_status"
                    value={formData.email_status}
                    onChange={handleChange}
                    className="select-field"
                  >
                    {EMAIL_STATUSES.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Phone Number
                  </label>
                  <input
                    type="text"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="e.g. +91 98311 00000"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Contact Person / Owner
                  </label>
                  <input
                    type="text"
                    name="contact_person"
                    value={formData.contact_person}
                    onChange={handleChange}
                    placeholder="e.g. John Doe (Founder)"
                    className="input-field"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Location & Address */}
          {activeTab === 'location' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">
                  Full Street Address
                </label>
                <input
                  type="text"
                  name="address"
                  value={formData.address}
                  onChange={handleChange}
                  placeholder="e.g. 18 Park Street, Suite 402"
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    placeholder="e.g. Kolkata"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    State / Province
                  </label>
                  <input
                    type="text"
                    name="state"
                    value={formData.state}
                    onChange={handleChange}
                    placeholder="e.g. West Bengal"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    name="country"
                    value={formData.country}
                    onChange={handleChange}
                    placeholder="e.g. India"
                    className="input-field"
                  />
                </div>
              </div>

              <div className="w-1/2 pr-2">
                <label className="block text-xs font-semibold text-neutral-700 mb-1">
                  Postal / Zip Code
                </label>
                <input
                  type="text"
                  name="postal_code"
                  value={formData.postal_code}
                  onChange={handleChange}
                  placeholder="e.g. 700016"
                  className="input-field"
                />
              </div>

              <div className="p-3 bg-neutral-100 rounded-lg text-xs text-neutral-600">
                <p className="font-semibold text-black mb-0.5">Location Consistency Check:</p>
                <p>The system automatically cross-references cities and states (e.g. Kolkata ↔ West Bengal) to flag discrepancies.</p>
              </div>
            </div>
          )}

          {/* TAB 3: Status & CRM Source */}
          {activeTab === 'crm' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Lead Status
                  </label>
                  <select
                    name="lead_status"
                    value={formData.lead_status}
                    onChange={handleChange}
                    className="select-field"
                  >
                    {LEAD_STATUSES.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-neutral-700 mb-1">
                    Lead Source
                  </label>
                  <select
                    name="lead_source"
                    value={formData.lead_source}
                    onChange={handleChange}
                    className="select-field"
                  >
                    {LEAD_SOURCES.map((src) => (
                      <option key={src} value={src}>
                        {src}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2 border-t border-neutral-200">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="is_verified"
                    name="is_verified"
                    checked={formData.is_verified}
                    onChange={handleChange}
                    className="w-4 h-4 rounded text-black focus:ring-black border-neutral-300"
                  />
                  <label htmlFor="is_verified" className="text-xs font-medium text-neutral-900 select-none">
                    Mark this lead as <strong>Verified</strong> (confirms contact and business validity)
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: Notes & Remarks */}
          {activeTab === 'notes' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-700 mb-1">
                  Lead Notes / Remarks
                </label>
                <textarea
                  name="notes"
                  rows={6}
                  value={formData.notes}
                  onChange={handleChange}
                  placeholder="Enter custom remarks, follow-up history, client requirements, or web opportunity notes..."
                  className="input-field font-mono text-xs"
                />
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-4 border-t border-neutral-200 flex items-center justify-between">
            {isEditMode ? (
              <button
                type="button"
                onClick={handleDelete}
                disabled={saving}
                className="btn-danger text-xs"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete Lead</span>
              </button>
            ) : (
              <div></div>
            )}

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={saving}
                className="btn-secondary text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="btn-primary text-xs"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : isEditMode ? 'Save Changes' : 'Create Lead'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
