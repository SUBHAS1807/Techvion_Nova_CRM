import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import LeadModal from './LeadModal';

export default function Layout({ onLeadCreated }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [newLeadModalOpen, setNewLeadModalOpen] = useState(false);

  const handleLeadSaved = (lead, action) => {
    if (onLeadCreated) onLeadCreated(lead, action);
    // Dispatch custom event so any active page table re-fetches
    window.dispatchEvent(new CustomEvent('lead-updated', { detail: { lead, action } }));
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      {/* Sidebar Navigation */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col flex-1 min-w-0">
        <Header
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onOpenNewLeadModal={() => setNewLeadModalOpen(true)}
          onRefresh={() => window.dispatchEvent(new CustomEvent('refresh-leads'))}
        />

        <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Global New Lead Modal */}
      <LeadModal
        isOpen={newLeadModalOpen}
        onClose={() => setNewLeadModalOpen(false)}
        onSaveSuccess={handleLeadSaved}
      />
    </div>
  );
}
