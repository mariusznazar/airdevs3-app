import React, { useState } from 'react';
import { processWebPage, analyzeArxiv } from '../services/apiService';

interface CrawlResult {
  status: string;
  url: string;
  content: string;
  original_content: string;
  media_files: Array<{
    url: string;
    type: string;
    description: string;
  }>;
}

export const WebCrawler = () => {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<string | null>(null);

  const handleCrawl = async () => {
    if (!url) {
      setError('Please enter a URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const response = await processWebPage(url);
      if (response.status === 'success') {
        setResult(response);
      } else {
        setError(response.message || 'Failed to process webpage');
      }
    } catch (err) {
      setError('Error processing webpage: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeArxiv = async () => {
    setAnalyzing(true);
    setAnalysisStatus(null);
    setError(null);
    
    try {
      const response = await analyzeArxiv();
      if (response.status === 'success') {
        setAnalysisStatus('Analysis completed successfully');
      } else {
        setError(response.message || 'Failed to analyze document');
      }
    } catch (err) {
      setError('Error analyzing document: ' + (err as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-100">Web Crawler</h1>
        
        <div className="flex gap-4">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter webpage URL"
            className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:border-orange-500"
          />
          <button
            onClick={handleCrawl}
            disabled={loading}
            className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : 'Process'}
          </button>
        </div>

        {/* Analyze Arxiv Button */}
        {result?.url === 'https://centrala.ag3nts.org/dane/arxiv-draft.html' && (
          <div className="mt-4">
            <button
              onClick={handleAnalyzeArxiv}
              disabled={analyzing}
              className="w-full px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
            >
              {analyzing ? 'Analyzing...' : 'Analyze Arxiv Document'}
            </button>
            {analysisStatus && (
              <div className="mt-2 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400">
                {analysisStatus}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {error}
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-6">
          {/* Processed Content */}
          <div className="p-6 bg-gray-800 rounded-lg">
            <h2 className="text-xl font-semibold text-orange-400 mb-4">Processed Content</h2>
            <div className="prose prose-invert max-w-none">
              {result.content.split('\n').map((line, i) => (
                <p key={i} className="text-gray-300">{line}</p>
              ))}
            </div>
          </div>

          {/* Media Files */}
          {result.media_files.length > 0 && (
            <div className="p-6 bg-gray-800 rounded-lg">
              <h2 className="text-xl font-semibold text-orange-400 mb-4">Processed Media Files</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {result.media_files.map((media, index) => (
                  <div key={index} className="p-4 bg-gray-700 rounded-lg">
                    <div className="font-medium text-gray-200 mb-2">
                      {media.type === 'images' ? '🖼️ Image' : '🔊 Audio'}
                    </div>
                    <div className="text-sm text-gray-300 mb-2">
                      {media.description}
                    </div>
                    <a 
                      href={media.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-orange-400 hover:text-orange-300 text-sm"
                    >
                      View original file
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 