import React, { useState, useEffect } from 'react';
import { BarChart3, DollarSign, Package, AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react';
import { ordersAPI, isAdminLoggedIn } from '../services/api';
import { toast } from 'sonner';

const OrderStatistics = () => {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (isAdminLoggedIn()) {
      loadData();
    }
  }, []);

  const loadData = async () => {
    try {
      const [statsData, ordersData] = await Promise.all([
        ordersAPI.getStatistics(),
        ordersAPI.getAdminOrders({ limit: 50 })
      ]);
      setStats(statsData);
      setOrders(ordersData.items || []);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
    toast.success('Данные обновлены');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-6 h-6 text-orange-500" />
          <h2 className="text-xl font-semibold text-white">Статистика заказов</h2>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:text-white hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Обновить
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon={<Package className="w-5 h-5" />}
            label="Всего заказов"
            value={stats.totalOrders}
            color="blue"
          />
          <StatCard
            icon={<DollarSign className="w-5 h-5" />}
            label="Стоимость лейблов"
            value={`$${(stats.totalLabelCost || 0).toFixed(2)}`}
            color="red"
          />
          <StatCard
            icon={<DollarSign className="w-5 h-5" />}
            label="Оплачено пользователями"
            value={`$${(stats.totalUserPaid || 0).toFixed(2)}`}
            color="green"
          />
          <StatCard
            icon={<TrendingUp className="w-5 h-5" />}
            label="Общая прибыль"
            value={`$${(stats.totalProfit || 0).toFixed(2)}`}
            color="orange"
          />
        </div>
      )}

      {/* Low Profit Warning */}
      {stats && stats.lowProfitOrders > 0 && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          <span className="text-red-400">
            {stats.lowProfitOrders} заказов с прибылью менее $10
          </span>
        </div>
      )}

      {/* Orders Table */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-lg font-medium text-white">Последние заказы</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-800/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Дата</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Пользователь</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Перевозчик</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Маршрут</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">ShipEngine</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">Оплачено</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">Прибыль</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {orders.map((order, idx) => (
                <tr 
                  key={idx} 
                  className={`${order.isLowProfit ? 'bg-red-500/10' : 'hover:bg-gray-800/30'} transition-colors`}
                >
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {order.createdAt ? new Date(order.createdAt).toLocaleDateString('ru-RU') : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-300">
                    {order.telegram_username || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className="px-2 py-1 rounded-full text-xs font-medium" style={{
                      background: order.carrier === 'usps' ? 'rgba(59, 130, 246, 0.2)' :
                                  order.carrier === 'ups' ? 'rgba(234, 179, 8, 0.2)' :
                                  order.carrier === 'fedex' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(107, 114, 128, 0.2)',
                      color: order.carrier === 'usps' ? '#60a5fa' :
                             order.carrier === 'ups' ? '#fbbf24' :
                             order.carrier === 'fedex' ? '#a78bfa' : '#9ca3af'
                    }}>
                      {(order.carrier || 'N/A').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {order.shipFromCity || '?'} → {order.shipToCity || '?'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-300">
                    ${(order.labelCost || 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-green-400">
                    ${(order.userPaid || 0).toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${
                    order.isLowProfit ? 'text-red-400' : 'text-green-400'
                  }`}>
                    ${(order.profit || 0).toFixed(2)}
                    {order.isLowProfit && (
                      <AlertTriangle className="w-4 h-4 inline ml-1 text-red-400" />
                    )}
                  </td>
                </tr>
              ))}
              {orders.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    Нет заказов
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ icon, label, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    green: 'bg-green-500/10 text-green-400 border-green-500/30',
    red: 'bg-red-500/10 text-red-400 border-red-500/30',
    orange: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  };

  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs uppercase tracking-wide opacity-80">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
};

export default OrderStatistics;
