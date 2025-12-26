import { DocViewer } from '../../components/docs/DocViewer'

const gettingStartedMd = `
## What is the Quality Dashboard?

The Quality Dashboard is a unified view of code quality signals across your repositories.
It combines static analysis, test results, and ML-based risk scores into a single UI so you
can decide **what to improve first**.

## Prerequisites

- Access to your source control platform (e.g. GitHub, GitLab, Bitbucket)
- An API token or OAuth app with read access to the repos you want to analyse
- (Optional) Access to your CI system if you want to ingest test and coverage data

## First run

1. **Open the dashboard** in your browser (local dev: \`npm run dev\`).
2. Use the **sidebar** to navigate to the overview page.
3. Connect your first repository (see “Connecting a repo”).
4. Wait for the initial analysis to complete.
5. Review the **summary cards**, **risk distribution**, and **top risky files**.

## Anatomy of the UI

- **Sidebar**: navigation between overview, repositories, modules, and classes.
- **Topbar**: environment information and dark/light mode toggle.
- **Overview page**: global metrics and top 10 risky files.
- **Repo / Module / Class pages**: drill-down into specific parts of your codebase.

Once a repo is connected and analysed, its risk scores, coverage trends, and prioritised
test plan will start to appear automatically.
`

export function GettingStartedPage() {
  return <DocViewer title="Getting started" markdown={gettingStartedMd} />
}


