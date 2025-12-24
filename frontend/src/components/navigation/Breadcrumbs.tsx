import { Link } from 'react-router-dom'

type Crumb = {
  label: string
  to?: string
}

type BreadcrumbsProps = {
  items: Crumb[]
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav
      className="flex flex-wrap items-center gap-1 text-xs text-slate-500 dark:text-slate-400"
      aria-label="Breadcrumb"
    >
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1
        return (
          <span key={idx} className="inline-flex items-center gap-1">
            {idx > 0 && <span className="text-slate-400">/</span>}
            {item.to && !isLast ? (
              <Link
                to={item.to}
                className="underline-offset-2 hover:underline hover:text-primary-500 dark:hover:text-primary-300"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className={
                  isLast
                    ? 'font-medium text-slate-700 dark:text-slate-100'
                    : ''
                }
              >
                {item.label}
              </span>
            )}
          </span>
        )
      })}
    </nav>
  )
}


