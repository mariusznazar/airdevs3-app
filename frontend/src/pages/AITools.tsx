import { useState } from 'react'
import TextLLM from '../components/TextLLM.tsx'
import AudioLLM from '../components/AudioLLM.tsx'
import ImageLLM from '../components/ImageLLM.tsx'

export const AITools = () => {
  const [activeTab, setActiveTab] = useState('text')

  return (
    <div>
      <div className="mb-4">
        <button
          className={`mr-2 px-4 py-2 rounded ${activeTab === 'text' ? 'bg-orange-500 text-white' : 'bg-gray-800 text-gray-300'}`}
          onClick={() => setActiveTab('text')}
        >
          Text
        </button>
        <button
          className={`mr-2 px-4 py-2 rounded ${activeTab === 'audio' ? 'bg-orange-500 text-white' : 'bg-gray-800 text-gray-300'}`}
          onClick={() => setActiveTab('audio')}
        >
          Audio
        </button>
        <button
          className={`px-4 py-2 rounded ${activeTab === 'image' ? 'bg-orange-500 text-white' : 'bg-gray-800 text-gray-300'}`}
          onClick={() => setActiveTab('image')}
        >
          Image
        </button>
      </div>

      <div className="mt-4">
        {activeTab === 'text' && <TextLLM />}
        {activeTab === 'audio' && <AudioLLM />}
        {activeTab === 'image' && <ImageLLM />}
      </div>
    </div>
  )
} 