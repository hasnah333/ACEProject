import { DocViewer } from '../../components/docs/DocViewer'

const shapMd = `
## SHAP explanations

SHAP (SHapley Additive exPlanations) is a way to explain **why** the ML model assigned
a particular risk score to a file, class, or module.

Each feature (like complexity, churn, or coverage) gets a **contribution value**:

- Positive values push the prediction **up** (towards higher risk).
- Negative values push the prediction **down** (towards lower risk).

## Local vs global explanations

- **Local explanation**:
  - Focuses on a single class or file.
  - Shows which features mattered most *for this specific case*.
  - Helps you decide what to refactor or test first.

- **Global explanation**:
  - Aggregates many examples.
  - Shows which features usually matter most across the whole system.
  - Helps you understand how the model thinks in general.

## Feature importance chart

The **feature importance bar chart** ranks features by absolute contribution. Longer bars
indicate features with a stronger influence on the risk score.

Typical features include:

- Churn in the last N days
- Cyclomatic complexity
- Recent test failures
- Coverage around the class or file

## Force / waterfall plot

The **force (waterfall) plot** shows how the model moves from a baseline risk level to the
final prediction by adding each feature's contribution in turn.

- Bars in **green** typically reduce risk.
- Bars in **red** increase risk.
- The final bar represents the predicted risk score.

## How to act on SHAP explanations

1. Identify the **top 2–3 features** that push risk up.
2. Ask whether you can:
   - Reduce complexity
   - Improve tests or coverage
   - Simplify dependencies
3. Use these insights to drive your **prioritised test plan** and refactoring roadmap.

The dashboard surfaces these explanations directly on class and module pages so you can
go from “this looks risky” to “here is exactly what we should improve” in a single view.
`

export function ShapExplanationsPage() {
  return <DocViewer title="SHAP explanations" markdown={shapMd} />
}


