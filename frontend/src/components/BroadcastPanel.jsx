import React, { useState, useEffect } from 'react';
import { Send, Users, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const BroadcastPanel = () => {
  const [message, setMessage] = useState('');
  const [parseMode, setParseMode] = useState('HTML');
  const [includeButton, setIncludeButton] = useState(false);
  const [buttonText, setButtonText] = useState('');
  const [buttonUrl, setButtonUrl] = useState('');
  const [usersCount, setUsersCount] = useState(0);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchUsersCount();
  }, []);

  const fetchUsersCount = async () => {
    try {
      const response = await axios.get(`${API}/broadcast/users-count`);
      setUsersCount(response.data.count);
    } catch (error) {
      console.error('Failed to fetch users count:', error);
    }
  };

  const handleSendBroadcast = async () => {
    if (!message.trim()) {
      toast.error('Введите текст сообщения');
      return;
    }

    if (includeButton && (!buttonText.trim() || !buttonUrl.trim())) {
      toast.error('Заполните текст и URL кнопки');
      return;
    }

    setSending(true);
    setResult(null);

    try {
      const response = await axios.post(`${API}/broadcast/send`, {
        message: message.trim(),
        parse_mode: parseMode,
        include_button: includeButton,
        button_text: buttonText.trim() || null,
        button_url: buttonUrl.trim() || null,
      });

      setResult(response.data);
      toast.success(`Рассылка завершена: ${response.data.sent}/${response.data.total_users} доставлено`);
    } catch (error) {
      console.error('Broadcast failed:', error);
      toast.error('Ошибка рассылки: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSending(false);
    }
  };

  const handleClear = () => {
    setMessage('');
    setIncludeButton(false);
    setButtonText('');
    setButtonUrl('');
    setResult(null);
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">📢 Рассылка</h1>
        <p className="text-slate-400">Массовая отправка сообщений всем пользователям бота</p>
      </div>

      {/* Users count card */}
      <div className="mb-6 p-4 rounded-lg" style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}>
        <div className="flex items-center gap-3">
          <Users className="text-blue-400" size={24} />
          <div>
            <p className="text-slate-400 text-sm">Всего пользователей</p>
            <p className="text-2xl font-bold text-white">{usersCount}</p>
          </div>
        </div>
      </div>

      {/* Message form */}
      <div className="space-y-4">
        {/* Parse mode selector */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Формат текста</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="parseMode"
                value="HTML"
                checked={parseMode === 'HTML'}
                onChange={(e) => setParseMode(e.target.value)}
                className="text-orange-500"
              />
              <span className="text-white">HTML</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="parseMode"
                value="Markdown"
                checked={parseMode === 'Markdown'}
                onChange={(e) => setParseMode(e.target.value)}
                className="text-orange-500"
              />
              <span className="text-white">Markdown</span>
            </label>
          </div>
        </div>

        {/* Message textarea */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Текст сообщения
          </label>
          <textarea
            data-testid="broadcast-message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={parseMode === 'HTML' 
              ? "Привет! 👋\n\n<b>Важное объявление:</b>\nНовые тарифы на доставку!\n\n<i>Подробнее по кнопке ниже</i>"
              : "Привет! 👋\n\n*Важное объявление:*\nНовые тарифы на доставку!\n\n_Подробнее по кнопке ниже_"
            }
            rows={8}
            className="w-full px-4 py-3 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            style={{ backgroundColor: '#0F172A', border: '1px solid #334155' }}
          />
          <p className="mt-1 text-xs text-slate-500">
            {parseMode === 'HTML' 
              ? 'Поддерживается: <b>жирный</b>, <i>курсив</i>, <code>код</code>, <a href="url">ссылка</a>'
              : 'Поддерживается: *жирный*, _курсив_, `код`, [ссылка](url)'
            }
          </p>
        </div>

        {/* Button toggle */}
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="includeButton"
            checked={includeButton}
            onChange={(e) => setIncludeButton(e.target.checked)}
            className="w-4 h-4 rounded text-orange-500 focus:ring-orange-500"
          />
          <label htmlFor="includeButton" className="text-white cursor-pointer">
            Добавить кнопку со ссылкой
          </label>
        </div>

        {/* Button fields */}
        {includeButton && (
          <div className="grid grid-cols-2 gap-4 p-4 rounded-lg" style={{ backgroundColor: '#0F172A', border: '1px solid #334155' }}>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Текст кнопки
              </label>
              <input
                type="text"
                value={buttonText}
                onChange={(e) => setButtonText(e.target.value)}
                placeholder="Подробнее"
                className="w-full px-4 py-2 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
                style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                URL кнопки
              </label>
              <input
                type="url"
                value={buttonUrl}
                onChange={(e) => setButtonUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full px-4 py-2 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
                style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}
              />
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-4 pt-4">
          <button
            data-testid="send-broadcast-btn"
            onClick={handleSendBroadcast}
            disabled={sending || !message.trim()}
            className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: sending ? '#475569' : '#F97316' }}
          >
            {sending ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                Отправка...
              </>
            ) : (
              <>
                <Send size={20} />
                Отправить всем ({usersCount})
              </>
            )}
          </button>
          <button
            onClick={handleClear}
            disabled={sending}
            className="px-6 py-3 rounded-lg font-medium text-slate-300 transition-colors hover:text-white disabled:opacity-50"
            style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}
          >
            Очистить
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="mt-6 p-4 rounded-lg" style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}>
          <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <CheckCircle className="text-green-400" size={20} />
            Результат рассылки
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-2xl font-bold text-white">{result.total_users}</p>
              <p className="text-sm text-slate-400">Всего</p>
            </div>
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-2xl font-bold text-green-400">{result.sent}</p>
              <p className="text-sm text-slate-400">Доставлено</p>
            </div>
            <div className="text-center p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <p className="text-2xl font-bold text-red-400">{result.failed}</p>
              <p className="text-sm text-slate-400">Ошибки</p>
            </div>
          </div>
          
          {result.failed_users && result.failed_users.length > 0 && (
            <div>
              <p className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                <AlertCircle className="text-yellow-400" size={16} />
                Ошибки доставки (первые 20):
              </p>
              <div className="max-h-32 overflow-y-auto text-xs text-slate-400 p-2 rounded" style={{ backgroundColor: '#0F172A' }}>
                {result.failed_users.map((err, idx) => (
                  <div key={idx} className="mb-1">{err}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tips */}
      <div className="mt-6 p-4 rounded-lg" style={{ backgroundColor: 'rgba(249, 115, 22, 0.1)', border: '1px solid rgba(249, 115, 22, 0.3)' }}>
        <h4 className="text-orange-400 font-medium mb-2">💡 Советы</h4>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• Telegram ограничивает отправку до 30 сообщений в секунду</li>
          <li>• Пользователи, заблокировавшие бота, не получат сообщение</li>
          <li>• Используйте эмодзи для привлечения внимания</li>
          <li>• Проверьте форматирование перед отправкой</li>
        </ul>
      </div>
    </div>
  );
};

export default BroadcastPanel;
