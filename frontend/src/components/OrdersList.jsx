import React, { useState, useEffect } from 'react';
import { Package, Filter, ExternalLink, AlertTriangle } from 'lucide-react';
import { ordersAPI } from '../services/api';
import { useNavigate } from 'react-router-dom';

const OrdersList = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    carrier: '',
    status: '',
  });
  const navigate = useNavigate();

  useEffect(() => {
    loadOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const params = {};
      if (filters.carrier) params.carrier = filters.carrier;
      if (filters.status) params.status = filters.status;
      
      const data = await ordersAPI.getOrders(params);
      setOrders(data.items || []);
    } catch (error) {
      console.error('Error loading orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Calculate profit for each order
  const getProfit = (order) => {
    const labelCost = order.labelCost || 0;
    const userPaid = order.userPaid || (labelCost + 10); // Default markup $10
    return userPaid - labelCost;
  };

  const isLowProfit = (order) => {
    return getProfit(order) < 10;
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 data-testid="orders-title" className="text-4xl font-bold mb-2">Orders</h1>
          <p className="text-muted" style={{ color: '#94A3B8' }}>Manage your shipping labels</p>
        </div>
        <button
          data-testid="create-order-btn"
          className="btn-primary"
          onClick={() => navigate('/create')}
        >
          Create New Label
        </button>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="flex gap-4 items-center">
          <div className="flex items-center gap-2">
            <Filter size={20} color="#94A3B8" />
            <span style={{ color: '#94A3B8' }}>Filters:</span>
          </div>
          
          <select
            data-testid="carrier-filter"
            className="input"
            style={{ width: 'auto', minWidth: '150px' }}
            value={filters.carrier}
            onChange={(e) => setFilters({ ...filters, carrier: e.target.value })}
          >
            <option value="">All Carriers</option>
            <option value="usps">USPS</option>
            <option value="fedex">FedEx</option>
            <option value="ups">UPS</option>
          </select>

          <select
            data-testid="status-filter"
            className="input"
            style={{ width: 'auto', minWidth: '150px' }}
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="label_created">Label Created</option>
            <option value="shipped">Shipped</option>
            <option value="delivered">Delivered</option>
          </select>

          <button
            data-testid="reset-filters-btn"
            className="btn-secondary"
            onClick={() => setFilters({ carrier: '', status: '' })}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Orders Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="loading-spinner"></div>
        </div>
      ) : orders.length === 0 ? (
        <div className="card text-center py-12">
          <Package size={48} color="#94A3B8" className="mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">No orders found</h3>
          <p style={{ color: '#94A3B8' }}>Create your first shipping label to get started</p>
          <button
            data-testid="empty-create-btn"
            className="btn-primary mt-4"
            onClick={() => navigate('/create')}
          >
            Create Label
          </button>
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid #1E293B' }}>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Tracking #</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>User</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Carrier</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Route</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Status</th>
                <th className="text-right py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>ShipEngine</th>
                <th className="text-right py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>User Paid</th>
                <th className="text-right py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Profit</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Created</th>
                <th className="text-left py-3 px-4" style={{ color: '#94A3B8', fontWeight: 500 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order, index) => {
                const profit = getProfit(order);
                const lowProfit = isLowProfit(order);
                const userPaid = order.userPaid || ((order.labelCost || 0) + 10);
                
                return (
                  <tr
                    key={order.id || index}
                    data-testid={`order-row-${index}`}
                    style={{ 
                      borderBottom: '1px solid #1E293B',
                      backgroundColor: lowProfit && order.status === 'label_created' ? 'rgba(239, 68, 68, 0.1)' : 'transparent'
                    }}
                    className="hover:bg-white/5 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <span className="mono" style={{ fontSize: '0.875rem' }}>
                        {order.trackingNumber || 'Pending'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span style={{ color: '#60A5FA', fontSize: '0.875rem' }}>
                        {order.telegram_username ? `@${order.telegram_username}` : order.telegram_user_id || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="uppercase font-medium">{order.carrier}</span>
                    </td>
                    <td className="py-3 px-4" style={{ color: '#94A3B8' }}>
                      {order.shipFromAddress?.city}, {order.shipFromAddress?.state} → {order.shipToAddress?.city}, {order.shipToAddress?.state}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`status-badge status-${order.status}`}>
                        {order.status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right" style={{ color: '#EF4444' }}>
                      ${(order.labelCost || 0).toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right" style={{ color: '#22C55E' }}>
                      ${userPaid.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span 
                        className="font-medium flex items-center justify-end gap-1"
                        style={{ color: lowProfit ? '#EF4444' : '#22C55E' }}
                      >
                        ${profit.toFixed(2)}
                        {lowProfit && order.status === 'label_created' && (
                          <AlertTriangle size={14} />
                        )}
                      </span>
                    </td>
                    <td className="py-3 px-4" style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
                      {formatDate(order.createdAt)}
                    </td>
                    <td className="py-3 px-4">
                      {order.labelDownloadUrl && (
                        <a
                          data-testid={`download-label-${index}`}
                          href={order.labelDownloadUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:text-primary/80"
                          style={{ color: '#F97316' }}
                        >
                          <ExternalLink size={16} />
                          <span>Label</span>
                        </a>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default OrdersList;
