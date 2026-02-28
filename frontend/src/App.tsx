import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LandingPage from './pages/LandingPage'
import DashboardPage from './pages/DashboardPage'
import PipelinePage from './pages/PipelinePage'
import AnalyticsPage from './pages/AnalyticsPage'
import ReportsPage from './pages/ReportsPage'
import ReportViewPage from './pages/ReportViewPage'
import AssistantPage from './pages/AssistantPage'

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* Landing page — no navbar */}
                <Route path="/" element={<LandingPage />} />

                {/* App pages — shared navbar layout */}
                <Route element={<Layout />}>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/pipeline" element={<PipelinePage />} />
                    <Route path="/analytics" element={<AnalyticsPage />} />
                    <Route path="/reports" element={<ReportsPage />} />
                    <Route path="/assistant" element={<AssistantPage />} />
                </Route>

                {/* Full-screen Report Viewer — standalone route without the standard Layout navbar */}
                <Route path="/reports/:filename" element={<ReportViewPage />} />
            </Routes>
        </BrowserRouter>
    )
}
