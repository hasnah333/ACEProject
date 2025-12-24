import type { ReactNode } from 'react'

type DataTableProps = {
  header: ReactNode
  children: ReactNode
}

export function DataTable({ header, children }: DataTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200/70 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-950/50">
      <table className="min-w-full text-xs">
        {header}
        <tbody className="divide-y divide-slate-200/70 bg-white/80 dark:divide-slate-800 dark:bg-slate-950/60">
          {children}
        </tbody>
      </table>
    </div>
  )
}


