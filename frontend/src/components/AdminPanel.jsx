import React, { useState, useEffect } from 'react';
import { Settings, Check, AlertCircle } from 'lucide-react';
import { adminAPI } from '../services/api';
import { toast } from 'sonner';

const AdminPanel = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedEnv, setSelectedEnv] = useState('sandbox');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await adminAPI.getConfig();
      setConfig(data);
      setSelectedEnv(data.environment);
    } catch (error) {
      console.error('Error loading config:', error);
      toast.error('Failed to load configuration');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="hero-glow py-8">
        <h1 data-testid="admin-title" className="text-4xl font-bold mb-2">Admin Panel</h1>
        <p className="text-muted" style={{ color: '#94A3B8' }}>Configure ShipEngine API settings</p>
      </div>

      <div className="max-w-2xl mt-8">
        {/* API Environment Configuration */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-3 rounded" style={{ backgroundColor: 'rgba(249, 115, 22, 0.2)' }}>
              <Settings size={24} color="#F97316" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">API Environment</h2>
              <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>Switch between test and production keys</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block mb-2 font-medium">Current Environment</label>
              <div className="flex gap-4">
                <button
                  data-testid="sandbox-option"
                  className={`flex-1 p-4 rounded border-2 transition-all ${
                    selectedEnv === 'sandbox'
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                  style={{
                    borderColor: selectedEnv === 'sandbox' ? '#F97316' : '#1E293B',
                    backgroundColor: selectedEnv === 'sandbox' ? 'rgba(249, 115, 22, 0.1)' : 'transparent',
                  }}
                  onClick={() => setSelectedEnv('sandbox')}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5"
                      style={{
                        borderColor: selectedEnv === 'sandbox' ? '#F97316' : '#1E293B',
                        backgroundColor: selectedEnv === 'sandbox' ? '#F97316' : 'transparent',
                      }}
                    >
                      {selectedEnv === 'sandbox' && <Check size={14} color="white" />}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold mb-1">Sandbox (Test)</div>
                      <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
                        Use test API keys. No real charges.
                      </p>
                    </div>
                  </div>
                </button>

                <button
                  data-testid="production-option"
                  className={`flex-1 p-4 rounded border-2 transition-all ${
                    selectedEnv === 'production'
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                  style={{
                    borderColor: selectedEnv === 'production' ? '#F97316' : '#1E293B',
                    backgroundColor: selectedEnv === 'production' ? 'rgba(249, 115, 22, 0.1)' : 'transparent',
                  }}
                  onClick={() => setSelectedEnv('production')}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5"
                      style={{
                        borderColor: selectedEnv === 'production' ? '#F97316' : '#1E293B',
                        backgroundColor: selectedEnv === 'production' ? '#F97316' : 'transparent',
                      }}
                    >
                      {selectedEnv === 'production' && <Check size={14} color="white" />}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold mb-1">Production (Live)</div>
                      <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
                        Use production API keys. Real charges apply.
                      </p>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            {selectedEnv !== config?.environment && (
              <div
                className="flex items-start gap-3 p-4 rounded"
                style={{ backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)' }}
              >
                <AlertCircle size={20} color="#F59E0B" className="mt-0.5" />
                <div>
                  <p className="font-medium" style={{ color: '#F59E0B' }}>Unsaved Changes</p>
                  <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
                    Click "Save Changes" to apply the new environment
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-4">
              <div>
                <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>Last updated: {new Date(config?.updated_at).toLocaleString()}</p>
              </div>
              <button
                data-testid="save-config-btn"
                className="btn-primary"
                onClick={handleSave}
                disabled={saving || selectedEnv === config?.environment}
                style={{
                  opacity: saving || selectedEnv === config?.environment ? 0.5 : 1,
                  cursor: saving || selectedEnv === config?.environment ? 'not-allowed' : 'pointer',
                }}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>

        {/* Information Card */}
        <div className="card mt-6" style={{ backgroundColor: 'rgba(14, 165, 233, 0.1)', border: '1px solid rgba(14, 165, 233, 0.3)' }}>
          <h3 className="font-semibold mb-2" style={{ color: '#0EA5E9' }}>API Keys Configuration</h3>
          <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
            API keys are stored securely in environment variables on the server. 
            To update API keys, modify the backend .env file and restart the server.
          </p>
          <ul className="mt-3 space-y-1" style={{ color: '#94A3B8', fontSize: '0.875rem' }}>
            <li>• SHIPENGINE_SANDBOX_KEY: Test API key</li>
            <li>• SHIPENGINE_PRODUCTION_KEY: Production API key</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;