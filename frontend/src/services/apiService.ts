import axios from 'axios';

// Add loading state management
let loadingState = {
  isLoading: false,
  setLoading: (state: boolean) => {
    loadingState.isLoading = state;
    if (loadingState.onLoadingChange) {
      loadingState.onLoadingChange(state);
    }
  },
  onLoadingChange: null as ((state: boolean) => void) | null
};

export const setLoadingCallback = (callback: (state: boolean) => void) => {
  loadingState.onLoadingChange = callback;
};

// Text processing endpoints
export const processText = async (text: string) => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/process-text', { text });
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

export const generateText = async (prompt: string) => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/generate-text', { prompt });
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

// Image processing endpoints
export const processImage = async (imageUrl: string) => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/process-image', { url: imageUrl });
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

// Audio processing endpoints
export const processAudio = async (audioUrl: string) => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/process-audio', { url: audioUrl });
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

// Web Crawler API endpoints
export const processWebPage = async (url: string) => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/process-webpage', { url });
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

export const analyzeArxiv = async () => {
  loadingState.setLoading(true);
  try {
    const response = await axios.post('/api/analyze-arxiv');
    return response.data;
  } finally {
    loadingState.setLoading(false);
  }
};

// PhotoAnalyzer API endpoints
export const photoAnalyzerApi = {
  startConversation: async () => {
    loadingState.setLoading(true);
    try {
      const response = await axios.post('/api/conversation/start');
      return response.data;
    } finally {
      loadingState.setLoading(false);
    }
  },

  sendCommand: async (command: string) => {
    loadingState.setLoading(true);
    try {
      const response = await axios.post('/api/conversation/command', { command });
      return response.data;
    } finally {
      loadingState.setLoading(false);
    }
  },

  sendDescription: async (description: string) => {
    loadingState.setLoading(true);
    try {
      const response = await axios.post('/api/conversation/description', { description });
      return response.data;
    } finally {
      loadingState.setLoading(false);
    }
  },

  clearCache: async () => {
    loadingState.setLoading(true);
    try {
      const response = await axios.post('/api/conversation/clear-cache');
      return response.data;
    } finally {
      loadingState.setLoading(false);
    }
  }
}; 