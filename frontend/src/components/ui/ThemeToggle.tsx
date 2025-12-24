import { useTheme } from './ThemeProvider'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex h-8 items-center gap-1 rounded-full border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 shadow-sm transition-colors duration-200 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
    >
      <span
        className="inline-block h-3 w-3 rounded-full bg-amber-400 transition-colors duration-200 dark:bg-sky-400"
      />
      <span>{theme === 'dark' ? 'Dark' : 'Light'} mode</span>
    </button>
  )
}


