import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ShipmentDock from './routes/ShipmentDock';
import ShipmentManifest from './routes/ShipmentManifest';
import ShipmentConsole from './routes/ShipmentConsole';
import SystemOverview from './routes/SystemOverview';
import EtdiPanel from './components/EtdiPanel';
import MachineState from './components/MachineState';
import SaturnNavLab from './shipments/saturnnav/SaturnNavLab';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <div className="bg-gradient-1" />
        <div className="bg-gradient-2" />

        <Sidebar />

        <main className="main-content">
          <div className="content-wrapper">
            <Routes>
              <Route path="/" element={<ShipmentDock />} />
              <Route path="/system" element={<SystemOverview />} />
              <Route path="/machine" element={<MachineState />} />
              <Route path="/etdi" element={<EtdiPanel />} />
              <Route path="/shipments/:id/manifest" element={<ShipmentManifest />} />
              <Route path="/shipments/saturnnav/lab" element={<SaturnNavLab />} />
              <Route path="/shipments/:id" element={<ShipmentConsole />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;