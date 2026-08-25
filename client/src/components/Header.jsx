import React from 'react';
import { Menu, Plus, RefreshCw, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Header({ onToggleSidebar, onOpenNewLeadModal, onRefresh }) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-neutral-200 px-4 lg:px-8 flex items-center justify-between shadow-xs">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg text-neutral-600 hover:text-black hover:bg-neutral-100 transition-colors"
          aria-label="Toggle Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:flex items-center gap-2 text-xs text-neutral-500 font-mono">
          <span className="w-2 h-2 rounded-full bg-black"></span>
          <span>TECHVION NOVA PRO CRM</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {onRefresh && (
          <button
            onClick={onRefresh}
            title="Refresh Data"
            className="p-2 text-neutral-600 hover:text-black hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={() => navigate('/leads')}
          className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-neutral-100 text-neutral-700 hover:bg-neutral-200 rounded-lg text-xs font-medium transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-neutral-500" />
          <span>Search CRM...</span>
        </button>

        <button
          onClick={onOpenNewLeadModal}
          className="btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" />
          <span>New Lead</span>
        </button>
      </div>
    </header>
  );
}
