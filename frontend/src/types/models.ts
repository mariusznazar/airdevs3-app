export interface AIModel {
  id: string;
  name: string;
  type?: 'text' | 'image' | 'audio';
  types?: ('text' | 'image' | 'audio')[];
  description?: string;
} 