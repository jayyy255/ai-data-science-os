import { create } from 'zustand';

export const useThemeStore = create((set) => ({
  theme: document.documentElement.dataset.theme || 'light',
  toggleTheme: () => set((state) => {
    const theme = state.theme === 'light' ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('aidso-theme', theme); } catch { /* Theme still works when storage is unavailable. */ }
    return { theme };
  }),
}));
