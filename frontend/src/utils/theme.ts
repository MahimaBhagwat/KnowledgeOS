export type Theme = 'dark' | 'obsidian' | 'midnight';

export function applyTheme(theme: string): void {
  const validTheme: Theme = ['dark', 'obsidian', 'midnight'].includes(theme)
    ? (theme as Theme)
    : 'dark';
  document.documentElement.setAttribute('data-theme', validTheme);
  localStorage.setItem('ko_theme', validTheme);
  window.dispatchEvent(new CustomEvent('ko-theme-change', { detail: validTheme }));
}

export function getInitialTheme(): Theme {
  const saved = localStorage.getItem('ko_theme');
  if (saved === 'obsidian' || saved === 'midnight' || saved === 'dark') {
    return saved;
  }
  return 'dark';
}
