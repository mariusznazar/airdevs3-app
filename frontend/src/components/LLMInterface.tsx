import React, { useState, useEffect } from 'react';
import { AIModel } from '../types/models';
import { fetchAvailableModels } from '../services/modelService';
import { processText, processImage, processAudio } from '../services/apiService';

type InputType = 'text' | 'audio' | 'image';

interface MessageFields {
  systemMessage: string;
  assistantMessage: string;
  userMessage: string;
}

interface Message {
  role: 'system' | 'assistant' | 'user';
  content: string;
}

export const LLMInterface: React.FC = () => {
  const [activeInput, setActiveInput] = useState<InputType>('text');
  const [messageFields, setMessageFields] = useState<MessageFields>({
    systemMessage: '',
    assistantMessage: '',
    userMessage: ''
  });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [model, setModel] = useState('');
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<string | null>(null);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const models = await fetchAvailableModels();
        setAvailableModels(models);
        // Set default model for current input type if available
        const defaultModel = models.find(m => m.type === activeInput);
        if (defaultModel) setModel(defaultModel.id);
      } catch (err) {
        setError('Failed to load available models');
      } finally {
        setIsLoading(false);
      }
    };

    loadModels();
  }, []);

  // Update selected model when input type changes
  useEffect(() => {
    const compatibleModel = availableModels.find(m => m.type === activeInput);
    if (compatibleModel) setModel(compatibleModel.id);
  }, [activeInput, availableModels]);

  const getCompatibleModels = () => {
    return availableModels.filter(m => 
      m.type === activeInput || // Single type match
      (m.types && m.types.includes(activeInput)) // Multi-type match
    );
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, type: 'audio' | 'image') => {
    const file = event.target.files?.[0];
    if (file) {
      if (type === 'audio') setAudioFile(file);
      else setImageFile(file);
    }
  };

  const handleMessageChange = (field: keyof MessageFields, value: string) => {
    setMessageFields(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const renderMessageFields = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">System Message</label>
        <textarea
          value={messageFields.systemMessage}
          onChange={(e) => handleMessageChange('systemMessage', e.target.value)}
          placeholder="Enter system message (e.g., 'You are a helpful assistant...')"
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Assistant Message</label>
        <textarea
          value={messageFields.assistantMessage}
          onChange={(e) => handleMessageChange('assistantMessage', e.target.value)}
          placeholder="Enter previous assistant message (optional)"
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>
    </div>
  );

  const renderTextForm = () => (
    <div className="space-y-4">
      {renderMessageFields()}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Your Message</label>
        <textarea
          value={messageFields.userMessage}
          onChange={(e) => handleMessageChange('userMessage', e.target.value)}
          placeholder="Enter your message here..."
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-32"
        />
      </div>
      <button 
        onClick={() => handleSubmit('text')}
        className="w-full bg-orange-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-orange-600"
      >
        Process Text
      </button>
    </div>
  );

  const renderAudioForm = () => (
    <div className="space-y-4">
      {renderMessageFields()}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Audio File</label>
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => handleFileChange(e, 'audio')}
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200"
        />
      </div>
      {audioFile && (
        <div className="text-sm text-gray-300">
          Selected file: {audioFile.name}
        </div>
      )}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Additional Message</label>
        <textarea
          value={messageFields.userMessage}
          onChange={(e) => handleMessageChange('userMessage', e.target.value)}
          placeholder="Enter any additional instructions or context..."
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>
      <button 
        onClick={() => handleSubmit('audio')}
        className="w-full bg-orange-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-orange-600"
      >
        Process Audio
      </button>
    </div>
  );

  const renderImageForm = () => (
    <div className="space-y-4">
      {renderMessageFields()}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Image File</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => handleFileChange(e, 'image')}
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200"
        />
      </div>
      {imageFile && (
        <div className="text-sm text-gray-300">
          Selected file: {imageFile.name}
        </div>
      )}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Additional Message</label>
        <textarea
          value={messageFields.userMessage}
          onChange={(e) => handleMessageChange('userMessage', e.target.value)}
          placeholder="Enter your question about the image..."
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200 h-24"
        />
      </div>
      <button 
        onClick={() => handleSubmit('image')}
        className="w-full bg-orange-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-orange-600"
      >
        Process Image
      </button>
    </div>
  );

  const handleSubmit = async (type: InputType) => {
    try {
      setIsLoading(true);
      setError(null);
      setResponse(null);
      const messages: Message[] = [];
      
      if (messageFields.systemMessage) {
        messages.push({
          role: 'system',
          content: messageFields.systemMessage
        });
      }
      
      if (messageFields.assistantMessage) {
        messages.push({
          role: 'assistant',
          content: messageFields.assistantMessage
        });
      }
      
      let apiResponse;
      if (type === 'text') {
        messages.push({
          role: 'user',
          content: messageFields.userMessage
        });

        apiResponse = await processText({
          model: model,
          messages: messages
        });
        
      } else if (type === 'image' && imageFile) {
        apiResponse = await processImage({
          model: model,
          messages: messages,
          imageFile: imageFile
        });
        
      } else if (type === 'audio' && audioFile) {
        apiResponse = await processAudio({
          model: model,
          messages: messages,
          audioFile: audioFile
        });
      }

      if (apiResponse?.status === 'success') {
        setResponse(apiResponse.data.content);
      } else {
        setError(apiResponse?.message || 'An error occurred');
      }
    } catch (error) {
      console.error('Error processing request:', error);
      setError('Failed to process request');
    } finally {
      setIsLoading(false);
    }
  };

  const renderModelSelection = () => {
    const compatibleModels = getCompatibleModels();

    if (isLoading) {
      return <div className="text-gray-300">Loading available models...</div>;
    }

    if (error) {
      return <div className="text-red-500">{error}</div>;
    }

    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">AI Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg shadow-sm text-gray-200"
        >
          {compatibleModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
              {m.description && ` - ${m.description}`}
            </option>
          ))}
        </select>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Input Type Selection */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setActiveInput('text')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors
            ${activeInput === 'text' 
              ? 'bg-orange-500 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
        >
          Text
        </button>
        <button
          onClick={() => setActiveInput('audio')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors
            ${activeInput === 'audio' 
              ? 'bg-orange-500 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
        >
          Audio
        </button>
        <button
          onClick={() => setActiveInput('image')}
          className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors
            ${activeInput === 'image' 
              ? 'bg-orange-500 text-white' 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
        >
          Image
        </button>
      </div>

      {/* Model Selection */}
      {renderModelSelection()}

      {/* Active Form */}
      {activeInput === 'text' && renderTextForm()}
      {activeInput === 'audio' && renderAudioForm()}
      {activeInput === 'image' && renderImageForm()}

      {/* Response Section */}
      {isLoading && (
        <div className="mt-4 p-4 bg-gray-700 rounded-lg">
          <div className="animate-pulse text-gray-400">Processing...</div>
        </div>
      )}
      
      {error && (
        <div className="mt-4 p-4 bg-red-900/50 border border-red-500 rounded-lg">
          <p className="text-red-500">{error}</p>
        </div>
      )}
      
      {response && (
        <div className="mt-4 p-4 bg-gray-700 border border-orange-500/20 rounded-lg">
          <h3 className="text-orange-500 font-medium mb-2">Response:</h3>
          <p className="text-gray-200 whitespace-pre-wrap">{response}</p>
        </div>
      )}
    </div>
  );
};

export default LLMInterface; 