import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Ban, Trash2, UserCheck, History } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = `${(process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '')}/api`;

const UsersManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [balanceAmount, setBalanceAmount] = useState('');
  const [balanceReason, setBalanceReason] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [balanceHistory, setBalanceHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/users/`);
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
      toast.error('Введите корректную сумму');
      return;
    }

    setIsUpdating(true);
    try {
      const response = await axios.post(`${API_URL}/users/balance`, {
        telegram_id: selectedUser.telegram_id,
        amount: isAdd ? amount : -amount,
        reason: balanceReason || (isAdd ? 'Пополнение баланса' : 'Списание средств')
      });
      
      setUsers(users.map(u => 
        u.telegram_id === selectedUser.telegram_id ? response.data : u
      ));
      setSelectedUser(response.data);
      setBalanceAmount('');
      setBalanceReason('');
      
      toast.success(`Баланс ${isAdd ? 'пополнен' : 'уменьшен'} на $${amount.toFixed(2)}`);
    } catch (error) {
      console.error('Error updating balance:', error);
      toast.error('Ошибка обновления баланса');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleBanUser = async (user) => {
    const isBanned = user.is_banned;
    const action = isBanned ? 'unban' : 'ban';
    
    try {
      await axios.post(`${API_URL}/users/${user.telegram_id}/${action}`);
      
      // Update user in list
      const updatedUsers = users.map(u => 
        u.telegram_id === user.telegram_id ? {...u, is_banned: !isBanned} : u
      );
      setUsers(updatedUsers);
      
      if (selectedUser?.telegram_id === user.telegram_id) {
        setSelectedUser({...selectedUser, is_banned: !isBanned});
      }
      
      toast.success(isBanned ? 'Пользователь разблокирован' : 'Пользователь заблокирован');
    } catch (error) {
      console.error('Error banning user:', error);
      toast.error('Ошибка при изменении статуса');
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    try {
      await axios.delete(`${API_URL}/users/${selectedUser.telegram_id}`);
      
      // Remove user from list
      setUsers(users.filter(u => u.telegram_id !== selectedUser.telegram_id));
      setSelectedUser(null);
      setShowDeleteConfirm(false);
      
      toast.success('Пользователь удалён');
    } catch (error) {
      console.error('Error deleting user:', error);
      toast.error('Ошибка удаления пользователя');
    }
  };

  const fetchBalanceHistory = async (telegramId) => {
    try {
      const response = await axios.get(`${API_URL}/users/${telegramId}/balance-history`);
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

  // Calculate total balance of all users
  const totalUsersBalance = users.reduce((sum, user) => sum + (user.balance || 0), 0);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Управление пользователями</h1>
      
      {/* Total Balance Summary Card */}
      <div className="mb-6 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg shadow-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm opacity-80 mb-1">Общий баланс всех пользователей</p>
            <p className="text-3xl font-bold">${totalUsersBalance.toFixed(2)}</p>
          </div>
          <div className="bg-white/20 rounded-full p-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-white/20 flex gap-6 text-sm">
          <div>
            <span className="opacity-70">Пользователей: </span>
            <span className="font-semibold">{users.length}</span>
          </div>
          <div>
            <span className="opacity-70">С балансом: </span>
            <span className="font-semibold">{users.filter(u => u.balance > 0).length}</span>
          </div>
          <div>
            <span className="opacity-70">Средний баланс: </span>
            <span className="font-semibold">${users.length > 0 ? (totalUsersBalance / users.length).toFixed(2) : '0.00'}</span>
          </div>
        </div>
      </div>
      
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
                    Статус
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Баланс
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Заказы
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
                    } ${user.is_banned ? 'bg-red-50' : ''}`}
                    onClick={() => setSelectedUser(user)}
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-medium ${
                          user.is_banned ? 'bg-red-500' : 'bg-blue-500'
                        }`}>
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
                    <td className="px-4 py-3 whitespace-nowrap">
                      {user.is_banned ? (
                        <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                          Заблокирован
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                          Активен
                        </span>
                      )}
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
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleBanUser(user);
                          }}
                          className={`p-1.5 rounded ${
                            user.is_banned 
                              ? 'bg-green-100 text-green-600 hover:bg-green-200' 
                              : 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200'
                          }`}
                          title={user.is_banned ? 'Разблокировать' : 'Заблокировать'}
                        >
                          {user.is_banned ? <UserCheck size={16} /> : <Ban size={16} />}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedUser(user);
                            setShowDeleteConfirm(true);
                          }}
                          className="p-1.5 rounded bg-red-100 text-red-600 hover:bg-red-200"
                          title="Удалить"
                        >
                          <Trash2 size={16} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            fetchBalanceHistory(user.telegram_id);
                            setSelectedUser(user);
                          }}
                          className="p-1.5 rounded bg-blue-100 text-blue-600 hover:bg-blue-200"
                          title="История"
                        >
                          <History size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
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
                  <span className="text-gray-500">Статус:</span>
                  <span className={`font-medium ${selectedUser.is_banned ? 'text-red-600' : 'text-green-600'}`}>
                    {selectedUser.is_banned ? '🚫 Заблокирован' : '✅ Активен'}
                  </span>
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
              </div>
              
              {/* Ban/Unban and Delete buttons */}
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleBanUser(selectedUser)}
                  className={`flex-1 py-2 px-3 rounded-lg font-medium text-sm flex items-center justify-center gap-1 ${
                    selectedUser.is_banned 
                      ? 'bg-green-500 hover:bg-green-600 text-white' 
                      : 'bg-yellow-500 hover:bg-yellow-600 text-white'
                  }`}
                >
                  {selectedUser.is_banned ? <UserCheck size={16} /> : <Ban size={16} />}
                  {selectedUser.is_banned ? 'Разблокировать' : 'Заблокировать'}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="flex-1 py-2 px-3 rounded-lg font-medium text-sm bg-red-500 hover:bg-red-600 text-white flex items-center justify-center gap-1"
                >
                  <Trash2 size={16} />
                  Удалить
                </button>
              </div>
            </div>
          )}

          {/* Balance Management */}
          {selectedUser && !selectedUser.is_banned && (
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 bg-white"
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Подтверждение удаления
            </h3>
            <p className="text-gray-600 mb-6">
              Вы уверены, что хотите удалить пользователя <strong>@{selectedUser.username || selectedUser.telegram_id}</strong>?
              <br /><br />
              Это действие удалит все данные пользователя, включая шаблоны. Пользователь получит уведомление об удалении.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 py-2 px-4 rounded-lg font-medium bg-gray-200 hover:bg-gray-300 text-gray-800"
              >
                Отмена
              </button>
              <button
                onClick={handleDeleteUser}
                className="flex-1 py-2 px-4 rounded-lg font-medium bg-red-500 hover:bg-red-600 text-white"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}

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
