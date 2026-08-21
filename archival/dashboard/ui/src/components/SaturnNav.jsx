import React from 'react';

const SaturnNav = () => {
  return (
    <div className="saturnnav-module animate-fade-in">
      <h2>SaturnNav Navigation Engine</h2>
      <div className="glass-panel mt-6">
        <h3>Preferential Routing</h3>
        <p className="mt-4 text-secondary">
          The SaturnNav module is currently offline. When active, it calculates bike-first, preferential routes through urban environments.
        </p>
        <div className="mt-6 p-4" style={{ border: '1px dashed var(--panel-border)', borderRadius: '8px', textAlign: 'center' }}>
          <span className="text-sm text-secondary">Map View Placeholder</span>
        </div>
      </div>
    </div>
  );
};

export default SaturnNav;
