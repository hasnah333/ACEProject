export function QualityFilterBar() {
  return (
    <div className="flex flex-wrap gap-2 items-center text-xs">
      <span className="text-slate-400">Filters</span>
      <button className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800">
        Time: Last 30 days
      </button>
      <button className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800">
        Scope: All repos
      </button>
      <button className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800">
        Signal: Test quality
      </button>
    </div>
  )
}


