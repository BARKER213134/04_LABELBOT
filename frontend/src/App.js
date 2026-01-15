import React from 'react';
import '@/App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import OrdersList from './components/OrdersList';
import CreateOrder from './components/CreateOrder';
import AdminPanel from './components/AdminPanel';
import UsersManagement from './components/UsersManagement';
import BroadcastPanel from './components/BroadcastPanel';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/orders" element={<OrdersList />} />
            <Route path="/create" element={<CreateOrder />} />
            <Route path="/users" element={<UsersManagement />} />
            <Route path="/broadcast" element={<BroadcastPanel />} />
            <Route path="/admin" element={<AdminPanel />} />
          </Routes>
        </div>
      </BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0F172A',
            color: '#F8FAFC',
            border: '1px solid #1E293B',
          },
        }}
      />
    </div>
  );
}

export default App;
