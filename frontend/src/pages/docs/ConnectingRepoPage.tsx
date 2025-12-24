import { DocViewer } from '../../components/docs/DocViewer'

const connectingRepoMd = `
## Connecting a repository

The dashboard analyses repositories by pulling metadata and, optionally, test + coverage
results from your existing tooling.

## 1. Provide repository details

From the overview or navigation:

1. Open **Repos** and click **Connect repo**.
2. Enter:
   - The repository URL (e.g. \`https://github.com/org/web-app\`)
   - The default branch (e.g. \`main\` or \`develop\`)
   - A short display name.

## 2. Configure authentication

Depending on your environment:

- **GitHub / GitLab cloud**: provide a personal access token or configure OAuth.
- **Self-hosted Git**: configure an access token or deploy the collector inside your network.

Tokens are stored securely and only used to:

- Read commits and files
- Fetch CI statuses (if integrated)

## 3. Enable CI and coverage ingestion (optional)

To show coverage trends and test results:

1. Configure your CI to publish coverage and test reports to the dashboard backend.
2. Map the reports to the repo and branch you just connected.

Once configured, the dashboard will:

- Recompute risk scores after new commits
- Update coverage charts
- Adjust the prioritised test plan

## 4. Verifying a new repo

After connecting:

1. Navigate to the repo page from the sidebar.
2. Confirm that:
   - Commits are visible
   - Modules and classes are listed
   - Risk scores are non-zero after the first analysis run
3. Check the **Top risky files** section for that repo to validate that the ranking looks sensible.
`

export function ConnectingRepoPage() {
  return <DocViewer title="Connecting a repository" markdown={connectingRepoMd} />
}


