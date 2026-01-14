import React, { useState, useEffect } from 'react';
import api from '../services/api';

const UsersManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [balanceAmount, setBalanceAmount] = useState('');
  const [balanceReason, setBalanceReason] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [balanceHistory, setBalanceHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/users/');
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBalanceUpdate = async (isAdd) => {
    if (!selectedUser || !balanceAmount) return;
    
    const amount = parseFloat(balanceAmount);
    if (isNaN(amount) || amount <= 0) {
      alert('Введите корректную сумму');
      return;
    }

    setIsUpdating(true);
    try {
      const response = await api.post('/users/balance', {
        telegram_id: selectedUser.telegram_id,
        amount: isAdd ? amount : -amount,
        reason: balanceReason || (isAdd ? 'Пополнение баланса' : 'Списание средств')
      });
      
      // Update user in list
      setUsers(users.map(u => 
        u.telegram_id === selectedUser.telegram_id ? response.data : u
      ));
      setSelectedUser(response.data);
      setBalanceAmount('');
      setBalanceReason('');
      
      alert(`Баланс ${isAdd ? 'пополнен' : 'уменьшен'} на $${amount.toFixed(2)}`);
    } catch (error) {
      console.error('Error updating balance:', error);
      alert('Ошибка обновления баланса');
    } finally {
      setIsUpdating(false);
    }
  };

  const fetchBalanceHistory = async (telegramId) => {
    try {
      const response = await api.get(`/users/${telegramId}/balance-history`);
      setBalanceHistory(response.data);
      setShowHistory(true);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('ru-RU');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Управление пользователями</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Users List */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b">
            <h2 className="font-semibold text-gray-700">
              Пользователи ({users.length})
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Пользователь
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Telegram ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Баланс
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Заказы
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Потрачено
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Действия
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr 
                    key={user.telegram_id}
                    className={`hover:bg-gray-50 cursor-pointer ${
                      selectedUser?.telegram_id === user.telegram_id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setSelectedUser(user)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-medium">
                          {(user.first_name || user.username || 'U')[0].toUpperCase()}
                        </div>
                        <div className="ml-3">
                          <div className="text-sm font-medium text-gray-900">
                            {user.first_name} {user.last_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            @{user.username || 'без username'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {user.telegram_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`text-sm font-semibold ${
                        user.balance > 0 ? 'text-green-600' : 'text-gray-500'
                      }`}>
                        ${user.balance?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {user.total_orders || 0}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      ${user.total_spent?.toFixed(2) || '0.00'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          fetchBalanceHistory(user.telegram_id);
                          setSelectedUser(user);
                        }}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        История
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                      Пользователей пока нет
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* User Details & Balance Management */}
        <div className="space-y-4">
          {/* Selected User Info */}
          {selectedUser && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold text-gray-700 mb-3">
                Выбранный пользователь
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Имя:</span>
                  <span className="font-medium">
                    {selectedUser.first_name} {selectedUser.last_name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Username:</span>
                  <span className="font-medium">@{selectedUser.username || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Telegram ID:</span>
                  <span className="font-medium">{selectedUser.telegram_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Баланс:</span>
                  <span className="font-semibold text-green-600">
                    ${selectedUser.balance?.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Всего заказов:</span>
                  <span className="font-medium">{selectedUser.total_orders}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Потрачено:</span>
                  <span className="font-medium">${selectedUser.total_spent?.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Регистрация:</span>
                  <span className="font-medium">{formatDate(selectedUser.created_at)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Balance Management */}
          {selectedUser && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold text-gray-700 mb-3">
                Управление балансом
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">
                    Сумма ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={balanceAmount}
                    onChange={(e) => setBalanceAmount(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">
                    Причина (опционально)
                  </label>
                  <input
                    type="text"
                    value={balanceReason}
                    onChange={(e) => setBalanceReason(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Причина изменения"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleBalanceUpdate(true)}
                    disabled={isUpdating || !balanceAmount}
                    className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    + Пополнить
                  </button>
                  <button
                    onClick={() => handleBalanceUpdate(false)}
                    disabled={isUpdating || !balanceAmount}
                    className="flex-1 bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    − Списать
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Balance History Modal */}
      {showHistory && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b flex justify-between items-center">
              <h3 className="font-semibold text-gray-700">
                История баланса: @{selectedUser.username}
              </h3>
              <button 
                onClick={() => setShowHistory(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="overflow-y-auto max-h-96">
              {balanceHistory.length > 0 ? (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Дата</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Сумма</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Баланс</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Причина</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {balanceHistory.map((entry, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-2 text-sm text-gray-500">
                          {formatDate(entry.timestamp)}
                        </td>
                        <td className={`px-4 py-2 text-sm font-medium ${
                          entry.amount >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {entry.amount >= 0 ? '+' : ''}{entry.amount?.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-700">
                          ${entry.new_balance?.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-sm text-gray-500">
                          {entry.reason || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-8 text-center text-gray-500">
                  История операций пуста
                </div>
              )}
            </div>
            <div className="px-4 py-3 bg-gray-50 border-t">
              <button
                onClick={() => setShowHistory(false)}
                className="w-full bg-gray-500 hover:bg-gray-600 text-white py-2 rounded-lg"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersManagement;
