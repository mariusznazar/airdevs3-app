interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string | Array<{ type: string; text?: string; image_url?: { url: string } }>;
}

interface ProcessRequestBase {
  model: string;
  messages: Message[];
}

interface ProcessTextRequest extends ProcessRequestBase {}

interface ProcessImageRequest extends ProcessRequestBase {
  imageFile: File;
}

interface ProcessAudioRequest extends ProcessRequestBase {
  audioFile: File;
}

const API_BASE_URL = 'http://localhost:8000/api';

export const processText = async (request: ProcessTextRequest) => {
  const response = await fetch(`${API_BASE_URL}/llm/text/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return await response.json();
};

export const processImage = async (request: ProcessImageRequest) => {
  const formData = new FormData();
  formData.append('image', request.imageFile);
  formData.append('data', JSON.stringify({
    model: request.model,
    messages: request.messages,
  }));

  const response = await fetch(`${API_BASE_URL}/llm/image/`, {
    method: 'POST',
    body: formData,
  });
  return await response.json();
};

export const processAudio = async (request: ProcessAudioRequest) => {
  const formData = new FormData();
  formData.append('audio', request.audioFile);
  formData.append('data', JSON.stringify({
    model: request.model,
    messages: request.messages,
  }));

  const response = await fetch(`${API_BASE_URL}/llm/audio/`, {
    method: 'POST',
    body: formData,
  });
  return await response.json();
}; 