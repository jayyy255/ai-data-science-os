import { Moon, Sun } from 'lucide-react';
import { useThemeStore } from '../store/useThemeStore';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore();
  const label = `Switch to ${theme === 'light' ? 'dark' : 'light'} mode`;
  const Icon = theme === 'light' ? Moon : Sun;
  return (
    <button type="button" onClick={toggleTheme} aria-label={label} title={label}
      className="theme-toggle glass-icon-button flex items-center justify-center gap-2 rounded-full border border-brand-dark-border px-2.5 text-zinc-300">
      <Icon className="h-4 w-4" />
      <span className="hidden md:inline text-xs font-medium">{theme === 'light' ? 'Light' : 'Dark'}</span>
    </button>
  );
}
