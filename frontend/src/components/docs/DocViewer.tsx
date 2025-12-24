import ReactMarkdown from 'react-markdown'
import { UiCard } from '../ui/UiCard'

type DocViewerProps = {
  title: string
  markdown: string
}

export function DocViewer({ title, markdown }: DocViewerProps) {
  return (
    <UiCard className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          {title}
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Documentation
        </p>
      </div>

      <div className="border-t border-slate-200 pt-4 text-sm leading-relaxed text-slate-800 dark:border-slate-800 dark:text-slate-200">
        <ReactMarkdown
          components={{
            h2: ({ node, ...props }: any) => (
              <h2
                className="mt-6 text-base font-semibold text-slate-900 dark:text-slate-50"
                {...props}
              />
            ),
            h3: ({ node, ...props }: any) => (
              <h3
                className="mt-4 text-sm font-semibold text-slate-900 dark:text-slate-50"
                {...props}
              />
            ),
            p: ({ node, ...props }: any) => (
              <p className="mt-2 text-sm text-slate-700 dark:text-slate-200" {...props} />
            ),
            ul: ({ node, ...props }: any) => (
              <ul
                className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200"
                {...props}
              />
            ),
            ol: ({ node, ...props }: any) => (
              <ol
                className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200"
                {...props}
              />
            ),
            code: ({ node, inline, ...props }: any) =>
              inline ? (
                <code
                  className="rounded bg-slate-100 px-1 py-0.5 text-xs text-slate-800 dark:bg-slate-900 dark:text-slate-100"
                  {...props}
                />
              ) : (
                <code
                  className="block rounded-md bg-slate-900 p-3 text-xs text-slate-100"
                  {...props}
                />
              ),
          }}
        >
          {markdown}
        </ReactMarkdown>
      </div>
    </UiCard>
  )
}


