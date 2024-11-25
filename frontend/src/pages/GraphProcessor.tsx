import React, { useState } from 'react';
import axios from 'axios';

interface ProcessResult {
  status: string;
  indexing?: {
    users_count: number;
    connections_count: number;
  };
  path?: string;
  message?: string;
  details?: any;
}

export const GraphProcessor = () => {
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProcess = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await axios.post<ProcessResult>('http://localhost:8000/api/graph/process/');
      setResult(response.data);
      
      if (response.data.status !== 'success') {
        setError(response.data.message || 'Unknown error occurred');
      }
    } catch (err) {
      setError('Error processing graph data: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Graph Processor</h1>
        <button
          onClick={handleProcess}
          disabled={loading}
          className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Processing...' : 'Process Graph Data'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {result && result.status === 'success' && (
        <div className="space-y-4">
          {/* Indexing Results */}
          <div className="p-4 bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-orange-400 mb-2">Indexing Results</h3>
            <div className="text-gray-300">
              <p>Users indexed: {result.indexing?.users_count}</p>
              <p>Connections indexed: {result.indexing?.connections_count}</p>
            </div>
          </div>

          {/* Path Results */}
          <div className="p-4 bg-gray-800 rounded-lg">
            <h3 className="text-lg font-semibold text-orange-400 mb-2">Shortest Path</h3>
            <p className="text-gray-300">{result.path}</p>
          </div>
        </div>
      )}
    </div>
  );
}; 