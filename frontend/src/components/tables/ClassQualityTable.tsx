const classes = [
  { id: '1', name: 'LoginController', coverage: 98, defects: 0 },
  { id: '2', name: 'InvoiceService', coverage: 79, defects: 2 },
]

export function ClassQualityTable() {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
      <header className="mb-3">
        <h2 className="text-sm font-semibold text-slate-100">
          Classes by risk
        </h2>
      </header>
      <div className="overflow-hidden border border-slate-800 rounded-lg">
        <table className="w-full text-xs">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Class</th>
              <th className="text-right px-3 py-2 font-medium">Coverage</th>
              <th className="text-right px-3 py-2 font-medium">Open defects</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-950">
            {classes.map((clazz) => (
              <tr key={clazz.id} className="hover:bg-slate-900/70">
                <td className="px-3 py-2 text-slate-100">{clazz.name}</td>
                <td className="px-3 py-2 text-right text-slate-100">
                  {clazz.coverage}%
                </td>
                <td className="px-3 py-2 text-right text-slate-100">
                  {clazz.defects}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}


