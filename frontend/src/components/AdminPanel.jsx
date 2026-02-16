import React, { useState, useEffect } from 'react';
import { Settings, Check, AlertCircle, Lock, LogOut, BarChart3 } from 'lucide-react';
import { adminAPI, isAdminLoggedIn, clearAdminAuth, setAdminAuth } from '../services/api';
import { toast } from 'sonner';
import OrderStatistics from './OrderStatistics';

const AdminLogin = ({ onLogin }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await adminAPI.login(username, password);
      toast.success('Вход выполнен успешно');
      onLogin();
    } catch (error) {
      toast.error('Неверный логин или пароль');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
      <div className="w-full max-w-md p-8 rounded-2xl" style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div className="flex items-center justify-center mb-8">
          <Lock className="w-12 h-12 text-orange-500" />
        </div>
        <h2 className="text-2xl font-bold text-center text-white mb-6">Admin Panel</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Логин</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-gray-800 text-white border border-gray-700 focus:border-orange-500 focus:outline-none"
              placeholder="admin"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-gray-800 text-white border border-gray-700 focus:border-orange-500 focus:outline-none"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
};

const AdminPanel = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(isAdminLoggedIn());
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState('sandbox');

  useEffect(() => {
    if (isLoggedIn) {
      loadConfig();
    }
  }, [isLoggedIn]);

  const loadConfig = async () => {
    try {
      const data = await adminAPI.getConfig();
      setConfig(data);
      setSelectedEnv(data.environment);
    } catch (error) {
      console.error('Error loading config:', error);
      if (error.response?.status === 401) {
        setIsLoggedIn(false);
      } else {
        toast.error('Failed to load configuration');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await adminAPI.updateConfig({
        environment: selectedEnv,
        updated_by: 'admin',
      });
      toast.success(`Switched to ${selectedEnv} environment`);
      await loadConfig();
    } catch (error) {
      console.error('Error saving config:', error);
      toast.error('Failed to update configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    clearAdminAuth();
    setIsLoggedIn(false);
    toast.info('Выход выполнен');
  };

  if (!isLoggedIn) {
    return <AdminLogin onLogin={() => setIsLoggedIn(true)} />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8" style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)' }}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Settings className="w-8 h-8 text-orange-500" />
            <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Выйти
          </button>
        </div>

        {/* Security Badge */}
        <div className="mb-6 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-2">
          <Lock className="w-4 h-4 text-green-500" />
          <span className="text-green-400 text-sm">Защищённое соединение</span>
        </div>

        {/* API Configuration Card */}
        <div className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,0.05)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.1)' }}>
          <div className="flex items-center gap-3 mb-2">
            <Settings className="w-6 h-6 text-orange-500" />
            <h2 className="text-xl font-semibold text-white">ShipEngine API Configuration</h2>
          </div>
          <p className="text-gray-400 mb-6" style={{ fontSize: '14px' }}>Configure ShipEngine API settings</p>

          {/* Environment Selector */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Sandbox Option */}
            <button
              onClick={() => setSelectedEnv('sandbox')}
              className={`p-4 rounded-xl border-2 transition-all ${
                selectedEnv === 'sandbox'
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-medium">🧪 Sandbox</span>
                {selectedEnv === 'sandbox' && <Check className="w-5 h-5 text-blue-500" />}
              </div>
              <p className="text-sm text-gray-400">Test environment with sample data</p>
            </button>

            {/* Production Option */}
            <button
              onClick={() => setSelectedEnv('production')}
              className={`p-4 rounded-xl border-2 transition-all ${
                selectedEnv === 'production'
                  ? 'border-orange-500 bg-orange-500/10'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-medium">🚀 Production</span>
                {selectedEnv === 'production' && <Check className="w-5 h-5 text-orange-500" />}
              </div>
              <p className="text-sm text-gray-400">Live environment with real shipping</p>
            </button>
          </div>

          {/* Current Status */}
          {config && (
            <div className="mb-6 p-4 rounded-xl bg-gray-800/50">
              <div className="flex items-center gap-2 mb-2">
                <div className={`w-2 h-2 rounded-full ${config.environment === 'production' ? 'bg-orange-500' : 'bg-blue-500'}`}></div>
                <span className="text-gray-300">Current: <span className="text-white font-medium">{config.environment}</span></span>
              </div>
              <p className="text-sm text-gray-500">Last updated: {new Date(config.updated_at).toLocaleString()}</p>
            </div>
          )}

          {/* Warning */}
          {selectedEnv === 'production' && (
            <div className="mb-6 p-4 rounded-xl bg-orange-500/10 border border-orange-500/30 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-orange-400 font-medium">Production Mode Warning</p>
                <p className="text-sm text-orange-300/80">Real shipping labels will be created and charged to your account.</p>
              </div>
            </div>
          )}

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={saving || selectedEnv === config?.environment}
            className={`w-full py-3 rounded-xl font-semibold transition-all ${
              saving || selectedEnv === config?.environment
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-orange-500 hover:bg-orange-600 text-white'
            }`}
          >
            {saving ? 'Saving...' : selectedEnv === config?.environment ? 'No Changes' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
