import type { ReactNode } from 'react'

type UiCardProps = {
  children: ReactNode
  className?: string
}

export function UiCard({ children, className = '' }: UiCardProps) {
  return (
    <section
      className={
        'rounded-xl border border-slate-200/70 bg-white/80 p-4 shadow-sm ' +
        'transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 ' +
        'dark:bg-slate-900/70 dark:border-slate-800 dark:hover:border-slate-700 ' +
        className
      }
    >
      {children}
    </section>
  )
}


