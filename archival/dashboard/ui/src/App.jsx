import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Overview from './components/Overview';
import Circadia from './components/Circadia';
import Arcadium from './components/Arcadium';
import SaturnNav from './components/SaturnNav';
import Sieve from './components/Sieve';
import './index.css';

function App() {
  const [activeModule, setActiveModule] = useState('overview');

  const renderModule = () => {
    switch (activeModule) {
      case 'overview': return <Overview />;
      case 'circadia': return <Circadia />;
      case 'arcadium': return <Arcadium />;
      case 'saturnnav': return <SaturnNav />;
      case 'sieve': return <Sieve />;
      default: return <Overview />;
    }
  };

  return (
    <div className="app-container">
      <div className="bg-gradient-1"></div>
      <div className="bg-gradient-2"></div>
      
      <Sidebar activeModule={activeModule} setActiveModule={setActiveModule} />
      
      <main className="main-content">
        <div className="content-wrapper">
          {renderModule()}
        </div>
      </main>
    </div>
  );
}

export default App;
