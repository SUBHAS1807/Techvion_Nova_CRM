import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Leads from './pages/Leads';
import ImportLeads from './pages/ImportLeads';
import WebsiteOpportunities from './pages/WebsiteOpportunities';
import DataQuality from './pages/DataQuality';
import Exports from './pages/Exports';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/import" element={<ImportLeads />} />
          <Route path="/website-opportunities" element={<WebsiteOpportunities />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="/exports" element={<Exports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
