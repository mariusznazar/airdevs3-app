import React, { useState } from 'react';
import axios from 'axios';

interface Tag {
  name: string;
  context: string;
}

interface TaggedFiles {
  [filename: string]: Tag[];
}

export const DocumentTagger = () => {
  const [result, setResult] = useState<TaggedFiles | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartTagging = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('http://localhost:8000/api/tag-documents/');
      setResult(response.data.data);
    } catch (err) {
      setError('Error tagging documents: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearTags = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await axios.post('http://localhost:8000/api/tag-documents/', { action: 'clear' });
      setResult(null);
    } catch (err) {
      setError('Error clearing tags: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Document Tagger</h1>
        <div className="space-x-4">
          <button
            onClick={handleClearTags}
            disabled={loading}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            Clear Tags
          </button>
          <button
            onClick={handleStartTagging}
            disabled={loading}
            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : 'Start Tagging'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="p-4 bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-orange-400 mb-4">Tagged Documents</h3>
            <div className="space-y-3">
              {Object.entries(result).map(([filename, tags]) => (
                <div key={filename} className="p-3 bg-gray-700/50 rounded-lg">
                  <div className="font-medium text-gray-200">{filename}</div>
                  <div className="mt-2 space-y-2">
                    {tags.map((tag, index) => (
                      <div key={index} className="flex items-start space-x-2 text-sm">
                        <span className="px-2 py-1 bg-orange-500/20 text-orange-300 rounded-md">
                          {tag.name}
                        </span>
                        <span className="text-gray-500 italic">
                          {tag.context}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}; 