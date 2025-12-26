import { DocViewer } from '../../components/docs/DocViewer'

const riskScoreMd = `
## Understanding the risk score

The **risk score** is a number between \`0\` and \`1\` that estimates how likely a piece
of code is to cause failures or defects in the near future.

- \`0.0 – 0.3\`: low risk
- \`0.3 – 0.7\`: medium risk
- \`0.7 – 1.0\`: high risk

## What drives the risk score?

The exact model can vary, but common signals include:

- **Change history**: recent churn, frequency of edits, and number of authors.
- **Complexity**: cyclomatic complexity, number of branches, and nesting depth.
- **Test coverage**: statement / branch coverage around the code.
- **Defect history**: how often this file, class, or module was involved in incidents.
- **Ownership**: whether the code has a clear owning team or is effectively orphaned.

The ML model combines these factors and produces a single score per file, class, or module.

## How to interpret it

- Use **relative ranking** more than absolute values.
- Focus first on:
  - High-risk areas with **low coverage**
  - High-risk areas with **recent production incidents**
- Use the score as a **guide for prioritisation**, not as a pass/fail gate.

## Where it appears in the UI

- **Overview**: global risk indicators and distribution.
- **Repo view**: risk per module and per file.
- **Module and class views**: detailed risk breakdown for a specific part of the code.

Combine the risk score with SHAP explanations to understand **why** the model thinks a
file or class is risky, then use the prioritised test plan to decide **what to do next**.
`

export function RiskScorePage() {
  return <DocViewer title="Understanding the risk score" markdown={riskScoreMd} />
}


