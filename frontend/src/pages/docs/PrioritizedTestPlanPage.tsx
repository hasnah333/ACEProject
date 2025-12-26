import { DocViewer } from '../../components/docs/DocViewer'

const planMd = `
## Generating a prioritised test plan

The prioritised test plan helps you decide **which tests or scenarios to run first** to
get the most risk reduction for the least effort.

## Inputs to the plan

The plan is generated from:

- **Risk scores** for files, classes, and modules.
- **Existing test coverage** and test results.
- **Historical defects** linked to code areas.
- (Optionally) **business criticality** tags or ownership metadata.

## How the plan is constructed

1. Rank classes and files by **risk score** (highest first).
2. Cross-check which areas have **weak or missing tests**.
3. Group related items into:
   - Test cases to add
   - Existing test suites to extend
   - Regression scenarios to run more frequently
4. Attach a **rough effort estimate** and **expected risk reduction** to each item.

## Reading the plan table

The plan table typically shows:

- **Item**: the class, module, or scenario to cover.
- **Risk**: current risk score.
- **Coverage**: current test coverage in percent.
- **Suggested action**: what kind of test work is recommended.
- **Priority**: a ranked order (P1, P2, P3) based on impact vs effort.

Start with P1 items that combine **high risk** and **low coverage**. Then move on to
P2 and P3 items as capacity allows.

## Exporting and sharing

Use the **Export CSV** and **Export PDF** actions on the plan view to:

- Share the plan with your team
- Attach it to planning documents
- Track progress over time

Updating code and tests will feed new data back into the model, which in turn will
update risk scores and regenerate an improved plan.
`

export function PrioritizedTestPlanPage() {
  return (
    <DocViewer title="Generating a prioritised test plan" markdown={planMd} />
  )
}


