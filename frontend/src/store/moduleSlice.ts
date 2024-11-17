import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface ModuleState {
  activeModules: string[];
  processingTasks: Record<string, string>;
  results: Record<string, any>;
}

const initialState: ModuleState = {
  activeModules: [],
  processingTasks: {},
  results: {}
}

const moduleSlice = createSlice({
  name: 'modules',
  initialState,
  reducers: {
    setActiveModules(state: ModuleState, action: PayloadAction<string[]>) {
      state.activeModules = action.payload
    },
    updateTaskStatus(
      state: ModuleState, 
      action: PayloadAction<{taskId: string, status: string}>
    ) {
      const { taskId, status } = action.payload
      state.processingTasks[taskId] = status
    },
    setResults(
      state: ModuleState, 
      action: PayloadAction<{taskId: string, results: any}>
    ) {
      const { taskId, results } = action.payload
      state.results[taskId] = results
    }
  }
})

export const { setActiveModules, updateTaskStatus, setResults } = moduleSlice.actions
export default moduleSlice.reducer 