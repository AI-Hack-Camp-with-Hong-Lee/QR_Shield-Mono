import { create } from 'zustand';
import type { ScanResult } from '../types';

interface AppStore {
  history: ScanResult[];
  addScan: (result: ScanResult) => void;
  deleteScan: (id: string) => void;
  clearHistory: () => void;
}

export const useStore = create<AppStore>((set) => ({
  history: [],
  addScan: (result) =>
    set((state) => ({ history: [result, ...state.history] })),
  deleteScan: (id) =>
    set((state) => ({ history: state.history.filter((r) => r.id !== id) })),
  clearHistory: () => set({ history: [] }),
}));
