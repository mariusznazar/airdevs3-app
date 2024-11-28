import React, { useState, useEffect } from 'react';
import { photoAnalyzerApi, setLoadingCallback } from '../services/apiService';

interface ProcessedImage {
  url: string;
  filename: string;
  description: string;
}

interface ConversationResponse {
  status: string;
  message: string;
  processed_images: ProcessedImage[];
  llm_analysis: string;
  suggested_actions: string[];
}

export const PhotoAnalyzer = () => {
  const [conversation, setConversation] = useState<ConversationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [actionQueue, setActionQueue] = useState<string[]>([]);
  const [processingActions, setProcessingActions] = useState(false);
  const [executedActions, setExecutedActions] = useState<Set<string>>(new Set());
  const [descriptionAttempts, setDescriptionAttempts] = useState<number>(0);
  const MAX_DESCRIPTION_ATTEMPTS = 2;

  // Set up loading callback
  useEffect(() => {
    setLoadingCallback(setLoading);
  }, []);

  // Process action queue
  useEffect(() => {
    const processNextAction = async () => {
      if (actionQueue.length > 0 && !processingActions) {
        setProcessingActions(true);
        const nextAction = actionQueue[0];
        
        // Sprawdź czy to SUBMIT_DESCRIPTION
        if (nextAction === "SUBMIT_DESCRIPTION") {
          console.log("Submitting generated description");
          const lastResponse = conversation[conversation.length - 1];
          if (lastResponse && lastResponse.llm_analysis) {
            try {
              const response = await photoAnalyzerApi.sendDescription(lastResponse.llm_analysis);
              if (response.status === 'success') {
                setConversation(prev => [...prev, response]);
                setDescriptionAttempts(prev => prev + 1);
                
                // Jeśli to nie ostatnia próba, kontynuuj analizę
                if (descriptionAttempts < MAX_DESCRIPTION_ATTEMPTS - 1) {
                  setActionQueue(["ANALYZE_ALL"]); // Rozpocznij nową analizę
                } else {
                  setActionQueue([]); // Zakończ proces po osiągnięciu limitu prób
                }
              } else {
                setError(response.message);
                setActionQueue(["ANALYZE_ALL"]); // Spróbuj ponownie w przypadku błędu
              }
            } catch (err) {
              setError('Error sending description: ' + (err as Error).message);
              setActionQueue(["ANALYZE_ALL"]); // Spróbuj ponownie w przypadku błędu
            }
            setProcessingActions(false);
            return;
          }
        }

        // Sprawdź czy akcja nie była już wykonana (pomijamy ANALYZE_ALL)
        if (nextAction !== "ANALYZE_ALL" && executedActions.has(nextAction)) {
          console.log(`Skipping already executed action: ${nextAction}`);
          setActionQueue(prev => {
            const remainingActions = prev.slice(1);
            // Jeśli wszystkie pozostałe akcje też były wykonane, dodaj ANALYZE_ALL
            if (remainingActions.every(action => 
              action !== "ANALYZE_ALL" && executedActions.has(action)
            )) {
              console.log("All suggested actions were already executed, adding ANALYZE_ALL");
              return ["ANALYZE_ALL"];
            }
            return remainingActions;
          });
          setProcessingActions(false);
          return;
        }
        
        console.log(`Processing action: ${nextAction}`);
        
        try {
          const response = await photoAnalyzerApi.sendCommand(nextAction);
          if (response.status === 'success') {
            setConversation(prev => [...prev, response]);
            
            // Dodaj akcję do wykonanych (pomijamy ANALYZE_ALL)
            if (nextAction !== "ANALYZE_ALL") {
              setExecutedActions(prev => new Set(prev).add(nextAction));
            }
            
            // Usuń wykonaną akcję i dodaj nowe
            if (response.suggested_actions && response.suggested_actions.length > 0) {
              setActionQueue(prev => {
                const newActions = response.suggested_actions.filter(
                  (action: string) => action === "ANALYZE_ALL" || !executedActions.has(action)
                );
                // Jeśli nie ma nowych akcji do wykonania, dodaj ANALYZE_ALL
                if (newActions.length === 0) {
                  console.log("No new actions available, adding ANALYZE_ALL");
                  return ["ANALYZE_ALL"];
                }
                return [...prev.slice(1), ...newActions];
              });
            } else {
              setActionQueue(prev => {
                const remainingActions = prev.slice(1);
                if (remainingActions.length === 0) {
                  console.log("No more actions in queue, adding ANALYZE_ALL");
                  return ["ANALYZE_ALL"];
                }
                return remainingActions;
              });
            }
          } else {
            setError(response.message);
            setActionQueue(prev => prev.slice(1));
          }
        } catch (err) {
          setError('Error executing command: ' + (err as Error).message);
          setActionQueue(prev => prev.slice(1));
        }
        
        setProcessingActions(false);
      }
    };

    const timer = setTimeout(processNextAction, 2000);
    return () => clearTimeout(timer);
  }, [actionQueue, processingActions, executedActions, conversation, descriptionAttempts]);

  const startConversation = async () => {
    setError(null);
    setDescriptionAttempts(0);  // Reset licznika prób opisu
    setExecutedActions(new Set());
    try {
      const response = await photoAnalyzerApi.startConversation();
      if (response.status === 'success') {
        setConversation([response]);
        if (response.suggested_actions && response.suggested_actions.length > 0) {
          setActionQueue(response.suggested_actions);
        }
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError('Error starting conversation: ' + (err as Error).message);
    }
  };

  const sendCommand = async (command: string) => {
    setError(null);
    // Add command to queue instead of executing immediately
    setActionQueue(prev => [...prev, command]);
  };

  const sendDescription = async () => {
    setError(null);
    // Only send description if no actions are pending
    if (actionQueue.length > 0) {
      setError('Please wait for all image processing to complete before sending description');
      return;
    }

    try {
      const response = await photoAnalyzerApi.sendDescription(description);
      if (response.status === 'success') {
        setConversation(prev => [...prev, response]);
        setDescription('');
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError('Error sending description: ' + (err as Error).message);
    }
  };

  const clearCache = async () => {
    if (loading || processingActions) return;
    
    const confirmClear = window.confirm(
      'Are you sure you want to clear all cached analyses? This action cannot be undone.'
    );
    
    if (!confirmClear) return;
    
    setError(null);
    try {
      const response = await photoAnalyzerApi.clearCache();
      if (response.status === 'success') {
        setConversation([]);
        setActionQueue([]);
        setDescription('');
        setExecutedActions(new Set());
        setDescriptionAttempts(0);  // Reset licznika prób opisu
        setError('Cache cleared successfully');
        setTimeout(() => setError(null), 3000);
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError('Error clearing cache: ' + (err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Photo Analyzer</h1>
        <div className="flex gap-4">
          <button
            onClick={clearCache}
            disabled={loading || processingActions}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            Clear Cache
          </button>
          <button
            onClick={startConversation}
            disabled={loading || processingActions}
            className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : 'Start Conversation'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {actionQueue.length > 0 && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <h3 className="text-blue-400 font-medium mb-2">Pending Actions:</h3>
          <ul className="list-disc list-inside text-blue-300">
            {actionQueue.map((action, index) => (
              <li key={index} className={executedActions.has(action) ? 'opacity-50' : ''}>
                {action}
                {executedActions.has(action) && ' (already executed)'}
              </li>
            ))}
          </ul>
        </div>
      )}

      {executedActions.size > 0 && (
        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
          <h3 className="text-green-400 font-medium mb-2">Executed Actions:</h3>
          <ul className="list-disc list-inside text-green-300">
            {Array.from(executedActions).map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-4">
        {conversation.map((response, index) => (
          <div key={index} className="p-4 bg-gray-800 rounded-lg space-y-4">
            <div className="text-gray-300">{response.message}</div>
            
            {response.processed_images.length > 0 && (
              <div className="grid grid-cols-2 gap-4">
                {response.processed_images.map((image, imgIndex) => (
                  <div key={imgIndex} className="space-y-2">
                    <img src={image.url} alt={image.filename} className="rounded-lg" />
                    <div className="text-sm text-gray-400">{image.description}</div>
                  </div>
                ))}
              </div>
            )}
            
            {response.llm_analysis && (
              <div className="text-gray-300 border-t border-gray-700 pt-4">
                {response.llm_analysis}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter description of Barbara..."
          disabled={actionQueue.length > 0}
          className="w-full h-32 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:outline-none focus:border-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={sendDescription}
          disabled={loading || !description || actionQueue.length > 0}
          className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
        >
          Send Description
        </button>
      </div>

      {descriptionAttempts > 0 && (
        <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-lg">
          <h3 className="text-purple-400 font-medium mb-2">Description Attempts</h3>
          <p className="text-purple-300">
            Attempt {descriptionAttempts} of {MAX_DESCRIPTION_ATTEMPTS}
          </p>
        </div>
      )}
    </div>
  );
}; 