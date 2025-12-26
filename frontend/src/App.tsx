import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { HomePage } from './pages/HomePage'
import { RepoPage } from './pages/RepoPage'
import { ModulePage } from './pages/ModulePage'
import { ClassPage } from './pages/ClassPage'
import { ModelsPage } from './pages/ModelsPage'
import { ThemeProvider } from './components/ui/ThemeProvider'
import { RepoProvider } from './context/RepoContext'
import { GettingStartedPage } from './pages/docs/GettingStartedPage'
import { ConnectingRepoPage } from './pages/docs/ConnectingRepoPage'
import { RiskScorePage } from './pages/docs/RiskScorePage'
import { ShapExplanationsPage } from './pages/docs/ShapExplanationsPage'
import { PrioritizedTestPlanPage } from './pages/docs/PrioritizedTestPlanPage'
import { ConnectRepoPage } from './pages/ConnectRepoPage'
import { MLPipelinePage } from './pages/MLPipelinePage'
import { AdvancedDashboardPage } from './pages/AdvancedDashboardPage'
import { PrioritizedTestPlanPage as TestPlanPage } from './pages/PrioritizedTestPlanPage'
import { AnalyseStatiquePage } from './pages/AnalyseStatiquePage'

function App() {
  return (
    <ThemeProvider>
      <RepoProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<HomePage />} />
              <Route path="repo/:id" element={<RepoPage />} />
              <Route path="module/:id" element={<ModulePage />} />
              <Route path="class/:id" element={<ClassPage />} />
              <Route path="models" element={<ModelsPage />} />
              <Route path="connect-repo" element={<ConnectRepoPage />} />
              <Route path="ml-pipeline" element={<MLPipelinePage />} />
              <Route path="advanced-dashboard" element={<AdvancedDashboardPage />} />
              <Route path="test-plan" element={<TestPlanPage />} />
              <Route path="analyse-statique" element={<AnalyseStatiquePage />} />
              <Route path="docs/getting-started" element={<GettingStartedPage />} />
              <Route path="docs/connecting-repo" element={<ConnectingRepoPage />} />
              <Route path="docs/risk-score" element={<RiskScorePage />} />
              <Route path="docs/shap-explanations" element={<ShapExplanationsPage />} />
              <Route
                path="docs/prioritised-test-plan"
                element={<PrioritizedTestPlanPage />}
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </RepoProvider>
    </ThemeProvider>
  )
}

export default App

