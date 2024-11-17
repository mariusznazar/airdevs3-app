import { AIModel } from '../types/models';

const API_BASE_URL = 'http://localhost:8000/api';

export const fetchAvailableModels = async (): Promise<AIModel[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/models/available`);
    if (!response.ok) throw new Error('Failed to fetch models');
    return await response.json();
  } catch (error) {
    console.error('Error fetching models:', error);
    throw error;
  }
}; 