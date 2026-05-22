import { Routes, Route } from 'react-router-dom'
import ReportsList from './pages/ReportsList'
import PairReport from './pages/PairReport'
import QueryDrillIn from './pages/QueryDrillIn'
import QueryStudio from './pages/QueryStudio'
import ReportsListV2 from './pages/ReportsListV2'
import PairReportV2 from './pages/PairReportV2'
import Trends from './pages/Trends'
import Nav from './components/Nav'

export default function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Nav />
      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<ReportsList />} />
          <Route path="/runs/:runId" element={<PairReport />} />
          <Route path="/runs/:runId/queries/:queryId" element={<QueryDrillIn />} />
          <Route path="/studio" element={<QueryStudio />} />
          <Route path="/v2" element={<ReportsListV2 />} />
          <Route path="/v2/runs/:runId" element={<PairReportV2 />} />
          <Route path="/v2/runs/:runId/queries/:queryId" element={<QueryDrillIn />} />
          <Route path="/trends" element={<Trends />} />
        </Routes>
      </main>
    </div>
  )
}
