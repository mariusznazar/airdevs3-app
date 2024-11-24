import React, { useState, useEffect } from 'react';
import { fetchAvailableModels } from '../services/modelService';
import { processText } from '../services/apiService';
import { AIModel, Message, MessageFields } from '../types/models';

const TextLLM: React.FC = () => {
  const [messageFields, setMessageFields] = useState<MessageFields>({
    systemMessage: '',
    assistantMessage: '',
    userMessage: ''
  });
  const [messages, setMessages] = useState<Message[]>([]);
  const [model, setModel] = useState('');
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const models = await fetchAvailableModels();
        const textModels = models.filter(m => m.type === 'text' || m.types?.includes('text'));
        setAvailableModels(textModels);
        if (textModels.length > 0) setModel(textModels[0].id);
      } catch (err) {
        setError('Failed to load available models');
      }
    };

    loadModels();
  }, []);

  const handleMessageChange = (field: keyof MessageFields, value: string) => {
    setMessageFields(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageFields.userMessage.trim()) return;

    setLoading(true);
    const messagesToSend: Message[] = [];
    
    if (messageFields.systemMessage) {
      messagesToSend.push({ role: 'system', content: messageFields.systemMessage });
    }
    if (messageFields.assistantMessage) {
      messagesToSend.push({ role: 'assistant', content: messageFields.assistantMessage });
    }
    messagesToSend.push({ role: 'user', content: messageFields.userMessage });

    try {
      const response = await processText({
        model: model,
        messages: messagesToSend
      });
      
      if (response.status === 'success') {
        setMessages(prev => [...prev, 
          { role: 'user', content: messageFields.userMessage },
          { role: 'assistant', content: response.data.content }
        ]);
        setMessageFields(prev => ({ ...prev, userMessage: '' }));
      }
    } catch (error) {
      console.error('Error:', error);
      setError('Failed to process message');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Model Selection */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">AI Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200"
        >
          {availableModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} {m.description && ` - ${m.description}`}
            </option>
          ))}
        </select>
      </div>

      {/* System Message */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">System Message</label>
        <textarea
          value={messageFields.systemMessage}
          onChange={(e) => handleMessageChange('systemMessage', e.target.value)}
          placeholder="Enter system message..."
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>

      {/* Assistant Message */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Assistant Message</label>
        <textarea
          value={messageFields.assistantMessage}
          onChange={(e) => handleMessageChange('assistantMessage', e.target.value)}
          placeholder="Enter previous assistant message..."
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>

      {/* Chat Messages */}
      <div className="space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-lg ${
              msg.role === 'user' ? 'bg-gray-800 ml-12' : 'bg-gray-700 mr-12'
            }`}
          >
            <p className="text-gray-300">{msg.content}</p>
          </div>
        ))}
      </div>

      {/* User Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          value={messageFields.userMessage}
          onChange={(e) => handleMessageChange('userMessage', e.target.value)}
          className="flex-1 bg-gray-800 text-gray-300 p-2 rounded-lg border border-gray-700 focus:border-orange-500 focus:outline-none"
          placeholder="Type your message..."
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-lg">
          <p className="text-red-500">{error}</p>
        </div>
      )}
    </div>
  );
};

export default TextLLM; 