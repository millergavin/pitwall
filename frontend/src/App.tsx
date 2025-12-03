import { Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { Championship } from './pages/Championship';
import { Circuits } from './pages/Circuits';
import { CircuitDetails } from './pages/CircuitDetails';
import { GrandPrix } from './pages/GrandPrix';
import { MeetingDetails } from './pages/MeetingDetails';
import { SessionDetails } from './pages/SessionDetails';
import { Drivers } from './pages/Drivers';
import { Teams } from './pages/Teams';
import { Admin } from './pages/Admin';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/championship" element={<Championship />} />
      <Route path="/circuits" element={<Circuits />} />
      <Route path="/circuits/:circuitId" element={<CircuitDetails />} />
      <Route path="/grand-prix" element={<GrandPrix />} />
      <Route path="/grand-prix/:meetingId" element={<MeetingDetails />} />
      <Route path="/sessions/:sessionId" element={<SessionDetails />} />
      <Route path="/drivers" element={<Drivers />} />
      <Route path="/teams" element={<Teams />} />
      <Route path="/admin" element={<Admin />} />
    </Routes>
  );
}

export default App;
