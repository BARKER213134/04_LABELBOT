import React, { useState, useEffect, useRef } from 'react';
import { Send, Users, AlertCircle, CheckCircle, Loader2, Image, X, Eye } from 'lucide-react';
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
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast.error('Файл слишком большой. Максимум 10MB');
        return;
      }
      if (!file.type.startsWith('image/')) {
        toast.error('Пожалуйста, выберите изображение');
        return;
      }
      setImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
      let response;
      
      if (image) {
        // Send with image using FormData
        const formData = new FormData();
        formData.append('message', message.trim());
        formData.append('parse_mode', parseMode);
        formData.append('include_button', includeButton);
        if (includeButton) {
          formData.append('button_text', buttonText.trim());
          formData.append('button_url', buttonUrl.trim());
        }
        formData.append('image', image);

        response = await axios.post(`${API}/broadcast/send-with-image`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        // Send text only
        response = await axios.post(`${API}/broadcast/send`, {
          message: message.trim(),
          parse_mode: parseMode,
          include_button: includeButton,
          button_text: buttonText.trim() || null,
          button_url: buttonUrl.trim() || null,
        });
      }

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
    removeImage();
  };

  // Format message for preview
  const formatPreviewText = (text) => {
    let formatted = text;
    
    if (parseMode === 'HTML') {
      // Replace HTML tags with actual formatting
      formatted = formatted
        .replace(/<b>/g, '<b>')
        .replace(/<\/b>/g, '</b>')
        .replace(/<i>/g, '<i>')
        .replace(/<\/i>/g, '</i>')
        .replace(/<code>/g, '<code class="bg-slate-700 px-1 rounded">')
        .replace(/<\/code>/g, '</code>')
        .replace(/<a href="([^"]+)">/g, '<a href="$1" class="text-blue-400 underline" target="_blank">')
        .replace(/<\/a>/g, '</a>')
        .replace(/\n/g, '<br/>');
    } else {
      // Markdown parsing
      formatted = formatted
        .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')  // **bold**
        .replace(/\*([^*]+)\*/g, '<b>$1</b>')      // *bold*
        .replace(/__([^_]+)__/g, '<i>$1</i>')      // __italic__
        .replace(/_([^_]+)_/g, '<i>$1</i>')        // _italic_
        .replace(/`([^`]+)`/g, '<code class="bg-slate-700 px-1 rounded">$1</code>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-400 underline" target="_blank">$1</a>')
        .replace(/\n/g, '<br/>');
    }
    
    return formatted;
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

      <div className="grid grid-cols-2 gap-6">
        {/* Left column - Form */}
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

          {/* Image upload */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Изображение (опционально)
            </label>
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
                id="image-upload"
              />
              <label
                htmlFor="image-upload"
                className="flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-colors hover:bg-slate-600"
                style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}
              >
                <Image size={20} className="text-slate-300" />
                <span className="text-slate-300">Выбрать фото</span>
              </label>
              {image && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
                  <span className="text-sm text-green-400">{image.name}</span>
                  <button onClick={removeImage} className="text-red-400 hover:text-red-300">
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>
            {imagePreview && (
              <div className="mt-3 relative inline-block">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="max-h-32 rounded-lg border border-slate-600"
                />
                <button
                  onClick={removeImage}
                  className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Message textarea */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              {image ? 'Подпись к изображению' : 'Текст сообщения'}
            </label>
            <textarea
              data-testid="broadcast-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={parseMode === 'HTML' 
                ? "Привет! 👋\n\n<b>Важное объявление:</b>\nНовые тарифы на доставку!\n\n<i>Подробнее по кнопке ниже</i>"
                : "Привет! 👋\n\n*Важное объявление:*\nНовые тарифы на доставку!\n\n_Подробнее по кнопке ниже_"
              }
              rows={6}
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
              onClick={() => setShowPreview(!showPreview)}
              className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-slate-300 transition-colors hover:text-white"
              style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}
            >
              <Eye size={20} />
              {showPreview ? 'Скрыть' : 'Превью'}
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

        {/* Right column - Preview */}
        <div>
          {showPreview && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Предварительный просмотр
              </label>
              <div 
                className="rounded-lg p-4"
                style={{ backgroundColor: '#0E1621', border: '1px solid #334155' }}
              >
                {/* Telegram-like message bubble */}
                <div className="max-w-sm">
                  <div 
                    className="rounded-lg overflow-hidden"
                    style={{ backgroundColor: '#182533' }}
                  >
                    {imagePreview && (
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="w-full max-h-64 object-cover"
                      />
                    )}
                    <div className="p-3">
                      <div 
                        className="text-white text-sm leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: formatPreviewText(message || 'Введите текст сообщения...') }}
                      />
                      {includeButton && buttonText && (
                        <div className="mt-3 pt-2 border-t border-slate-600">
                          <button 
                            className="w-full py-2 text-center text-blue-400 text-sm font-medium rounded hover:bg-slate-700 transition-colors"
                          >
                            {buttonText || 'Кнопка'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right mt-1">
                    <span className="text-xs text-slate-500">
                      {new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="mt-4 p-4 rounded-lg" style={{ backgroundColor: '#1E293B', border: '1px solid #334155' }}>
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
        </div>
      </div>

      {/* Tips */}
      <div className="mt-6 p-4 rounded-lg" style={{ backgroundColor: 'rgba(249, 115, 22, 0.1)', border: '1px solid rgba(249, 115, 22, 0.3)' }}>
        <h4 className="text-orange-400 font-medium mb-2">💡 Советы</h4>
        <ul className="text-sm text-slate-300 space-y-1">
          <li>• Telegram ограничивает отправку до 30 сообщений в секунду</li>
          <li>• Максимальный размер изображения: 10MB</li>
          <li>• Подпись к фото ограничена 1024 символами</li>
          <li>• Используйте эмодзи для привлечения внимания</li>
        </ul>
      </div>
    </div>
  );
};

export default BroadcastPanel;
