import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  UploadCloud,
  Globe2,
  ShieldCheck,
  FileSpreadsheet,
  Settings,
  Sparkles,
  X
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Leads', path: '/leads', icon: Users },
  { name: 'Import', path: '/import', icon: UploadCloud },
  { name: 'Website Opportunities', path: '/website-opportunities', icon: Globe2 },
  { name: 'Data Quality', path: '/data-quality', icon: ShieldCheck },
  { name: 'Exports', path: '/exports', icon: FileSpreadsheet },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-black text-white flex flex-col border-r border-neutral-800 transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-neutral-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold text-base shadow-sm">
              T
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-wider uppercase text-white">
                Techvion<span className="text-neutral-400">Nova</span>
              </h1>
              <p className="text-[10px] text-neutral-400 tracking-wider uppercase font-mono">
                Lead CRM Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-neutral-400 hover:text-white p-1 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">
            Core Modules
          </div>

          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => onClose && onClose()}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-white text-black font-semibold shadow-sm'
                      : 'text-neutral-300 hover:text-white hover:bg-neutral-900'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Footer Info */}
        <div className="p-4 border-t border-neutral-800 bg-neutral-950">
          <div className="bg-neutral-900 rounded-lg p-3 border border-neutral-800">
            <div className="flex items-center gap-2 text-xs font-medium text-neutral-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Lead CRM Active
            </div>
            <p className="text-[11px] text-neutral-400 mt-1">
              Data cleaning & verification engine online.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
