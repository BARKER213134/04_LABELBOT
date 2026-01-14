import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Package, Settings, Users } from 'lucide-react';

const Sidebar = () => {
  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/orders', icon: Package, label: 'Orders' },
    { path: '/users', icon: Users, label: 'Users' },
    { path: '/admin', icon: Settings, label: 'Admin' },
  ];

  return (
    <div className="sidebar">
      <div className="p-6">
        <h2 data-testid="app-title" className="text-2xl font-bold" style={{ color: '#F97316' }}>
          ShipBot
        </h2>
        <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>Label Management</p>
      </div>

      <nav className="mt-8">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.label.toLowerCase()}`}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 p-6">
        <div
          className="p-4 rounded"
          style={{
            backgroundColor: 'rgba(14, 165, 233, 0.1)',
            border: '1px solid rgba(14, 165, 233, 0.3)',
          }}
        >
          <p className="font-semibold mb-1" style={{ fontSize: '0.875rem' }}>
            Need Help?
          </p>
          <p style={{ color: '#94A3B8', fontSize: '0.75rem' }}>
            Check the admin panel for API configuration
          </p>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;