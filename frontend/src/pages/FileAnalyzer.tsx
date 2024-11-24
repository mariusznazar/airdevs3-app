import React, { useState } from 'react';
import axios from 'axios';

interface AnalysisResult {
  people: string[];
  hardware: string[];
}

export const FileAnalyzer = () => {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('http://localhost:8000/api/analyze-files/');
      setResult(response.data.data);
    } catch (err) {
      setError('Error analyzing files: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">File Analyzer</h1>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Analyzing...' : 'Analyze Files'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="p-4 bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-orange-400 mb-2">People</h3>
            <ul className="list-disc list-inside text-gray-300 space-y-1">
              {result.people.map(file => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          </div>

          <div className="p-4 bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-orange-400 mb-2">Hardware</h3>
            <ul className="list-disc list-inside text-gray-300 space-y-1">
              {result.hardware.map(file => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}; 