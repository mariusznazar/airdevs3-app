import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Analysis {
  file_name: string;
  file_type: string;
  category: string;
  content: string;
  created_at: string;
}

interface AnalysisSummary {
  total: number;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  analyses: Analysis[];
}

const AnalysisList: React.FC = () => {
  const [data, setData] = useState<AnalysisSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get<AnalysisSummary>('http://localhost:8000/api/analyses/');
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch analyses');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data available</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-orange-400">Total Analyses</h3>
          <p className="text-2xl text-gray-200">{data.total}</p>
        </div>
        <div className="p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-orange-400">By Type</h3>
          {Object.entries(data.by_type).map(([type, count]) => (
            <div key={type} className="flex justify-between text-gray-200">
              <span>{type}</span>
              <span>{count}</span>
            </div>
          ))}
        </div>
        <div className="p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-orange-400">By Category</h3>
          {Object.entries(data.by_category).map(([category, count]) => (
            <div key={category} className="flex justify-between text-gray-200">
              <span>{category || 'uncategorized'}</span>
              <span>{count}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-100">Analysis Results</h2>
        {data.analyses.map((analysis) => (
          <div key={analysis.file_name} className="p-4 bg-gray-800 rounded-lg">
            <div className="flex justify-between items-start mb-2">
              <h3 className="text-lg font-semibold text-orange-400">{analysis.file_name}</h3>
              <span className="px-2 py-1 bg-gray-700 rounded text-sm text-gray-300">
                {analysis.category || 'uncategorized'}
              </span>
            </div>
            <p className="text-gray-300 whitespace-pre-wrap">{analysis.content}</p>
            <div className="mt-2 text-sm text-gray-400">
              Analyzed: {new Date(analysis.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AnalysisList; 