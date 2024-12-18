import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { AITools } from './pages/AITools.tsx';
import { FileAnalyzer } from './pages/FileAnalyzer.tsx';
import { WebCrawler } from './pages/WebCrawler.tsx';
import { DocumentTagger } from './pages/DocumentTagger.tsx';
import { GraphProcessor } from './pages/GraphProcessor.tsx';
import { PhotoAnalyzer } from './pages/PhotoAnalyzer.tsx';

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900">
        <nav className="bg-black shadow-lg border-b border-orange-500/20">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="text-xl font-bold text-orange-500 hover:text-orange-400 transition-colors">
                  AirDevs App
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link
                  to="/ai-tools"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  AI Tools
                </Link>
                <Link
                  to="/file-analyzer"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  File Analyzer
                </Link>
                <Link
                  to="/web-crawler"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  Web Crawler
                </Link>
                <Link
                  to="/document-tagger"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  Document Tagger
                </Link>
                <Link
                  to="/graph-processor"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  Graph Processor
                </Link>
                <Link
                  to="/photo-analyzer"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-orange-400 hover:bg-gray-800 transition-colors"
                >
                  Photo Analyzer
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/ai-tools" replace />} />
            <Route path="/ai-tools" element={<AITools />} />
            <Route path="/file-analyzer" element={<FileAnalyzer />} />
            <Route path="/web-crawler" element={<WebCrawler />} />
            <Route path="/document-tagger" element={<DocumentTagger />} />
            <Route path="/graph-processor" element={<GraphProcessor />} />
            <Route path="/photo-analyzer" element={<PhotoAnalyzer />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App; 