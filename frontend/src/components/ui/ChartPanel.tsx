import type { ReactNode } from 'react'
import { UiCard } from './UiCard'
import { SectionHeader } from './SectionHeader'

type ChartPanelProps = {
  title: string
  subtitle?: string
  children: ReactNode
}

export function ChartPanel({ title, subtitle, children }: ChartPanelProps) {
  return (
    <UiCard className="h-full">
      <SectionHeader title={title} subtitle={subtitle} />
      <div className="h-64 sm:h-72 lg:h-80">
        <div className="h-full w-full rounded-lg border border-slate-200/60 bg-slate-50/60 transition-colors duration-200 dark:border-slate-800 dark:bg-slate-950/40">
          {children}
        </div>
      </div>
    </UiCard>
  )
}


