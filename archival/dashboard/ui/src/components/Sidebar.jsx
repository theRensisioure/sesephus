import React from 'react';

const Sidebar = ({ activeModule, setActiveModule }) => {
  const modules = [
    { id: 'overview', name: 'Overview', icon: '📊' },
    { id: 'circadia', name: 'Circadia', icon: '⏰' },
    { id: 'arcadium', name: 'Arcadium', icon: '🎙️' },
    { id: 'saturnnav', name: 'SaturnNav', icon: '🚴' },
    { id: 'sieve', name: 'Sieve', icon: '✂️' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        ⬡ <span>Sesephus</span>
      </div>
      
      <div className="nav-links">
        {modules.map(mod => (
          <div 
            key={mod.id}
            className={`nav-item ${activeModule === mod.id ? 'active' : ''}`}
            onClick={() => setActiveModule(mod.id)}
          >
            <span className="nav-icon">{mod.icon}</span>
            {mod.name}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;
