import React, { useState, useEffect } from 'react';
import { Package, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { statisticsAPI } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    try {
      const data = await statisticsAPI.getStatistics();
      setStats(data);
    } catch (error) {
      console.error('Error loading statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Orders',
      value: stats?.total_orders || 0,
      icon: Package,
      color: '#F97316',
    },
    {
      title: 'Recent Orders (7d)',
      value: stats?.recent_orders_7d || 0,
      icon: TrendingUp,
      color: '#0EA5E9',
    },
    {
      title: 'Total Cost',
      value: `$${stats?.total_cost || 0}`,
      icon: DollarSign,
      color: '#10B981',
    },
    {
      title: 'Active Labels',
      value: stats?.status_breakdown?.label_created || 0,
      icon: Activity,
      color: '#F59E0B',
    },
  ];

  const carrierData = Object.entries(stats?.carrier_breakdown || {}).map(([name, value]) => ({
    name: name.toUpperCase(),
    orders: value,
  }));

  const statusData = Object.entries(stats?.status_breakdown || {}).map(([name, value]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    count: value,
  }));

  return (
    <div className="p-8">
      <div className="hero-glow py-8">
        <h1 data-testid="dashboard-title" className="text-4xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted" style={{ color: '#94A3B8' }}>Overview of your shipping operations</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              data-testid={`stat-card-${index}`}
              className="card card-shimmer"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm" style={{ color: '#94A3B8' }}>{stat.title}</p>
                  <h3 className="text-3xl font-bold mt-2">{stat.value}</h3>
                </div>
                <div
                  className="p-3 rounded"
                  style={{ backgroundColor: `${stat.color}20` }}
                >
                  <Icon size={24} color={stat.color} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        {/* Carrier Distribution */}
        <div className="card">
          <h3 data-testid="carrier-chart-title" className="text-xl font-semibold mb-4">Orders by Carrier</h3>
          {carrierData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={carrierData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    border: '1px solid #1E293B',
                    borderRadius: '4px',
                  }}
                />
                <Bar dataKey="orders" fill="#F97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-8" style={{ color: '#94A3B8' }}>No data available</p>
          )}
        </div>

        {/* Status Distribution */}
        <div className="card">
          <h3 data-testid="status-chart-title" className="text-xl font-semibold mb-4">Orders by Status</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={statusData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis dataKey="name" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    border: '1px solid #1E293B',
                    borderRadius: '4px',
                  }}
                />
                <Bar dataKey="count" fill="#0EA5E9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-8" style={{ color: '#94A3B8' }}>No data available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;