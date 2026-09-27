import { Navigate, Route, Routes } from 'react-router-dom';
import Shell from './components/Shell';
import Overview from './pages/Overview';
import Analytics from './pages/Analytics';
import Evidence from './pages/Evidence';
import RecordDetail from './pages/RecordDetail';
import Copilot from './pages/Copilot';
import Methodology from './pages/Methodology';
import ClusterDetail from './pages/ClusterOverview';

export default function App() {
  return <Shell>
    <Routes>
      <Route path="/" element={<Overview />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/evidence" element={<Evidence />} />
      <Route path="/evidence/:id" element={<RecordDetail />} />
      <Route path="/copilot" element={<Copilot />} />
      <Route path="/methodology" element={<Methodology />} />
      <Route path="/cluster/:id" element={<ClusterDetail />} />
      <Route path="/funnel" element={<Navigate to="/analytics" replace />} />
      <Route path="/test-drive" element={<Navigate to="/copilot?tool=classifier" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </Shell>;
}
