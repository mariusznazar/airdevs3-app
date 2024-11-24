export interface AIModel {
  id: string;
  name: string;
  description?: string;
  type: 'text' | 'audio' | 'image';
  types?: ('text' | 'audio' | 'image')[];
}

export interface Message {
  role: 'system' | 'assistant' | 'user';
  content: string;
}

export interface MessageFields {
  systemMessage: string;
  assistantMessage: string;
  userMessage: string;
} 