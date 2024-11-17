import React from 'react';
import LLMInterface from '../components/LLMInterface';

export const AITools: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-orange-500 mb-2">AI Tools</h1>
          <p className="text-gray-400">Interact with AI models for text, image, and audio processing</p>
        </div>
        <div className="bg-gray-800 rounded-xl shadow-xl p-6 border border-orange-500/20">
          <LLMInterface />
        </div>
      </div>
    </div>
  );
}; 