import React from 'react';

const Circadia = () => {
  return (
    <div className="circadia-module animate-fade-in">
      <h2>Circadia Alarm Engine</h2>
      <div className="glass-panel mt-6">
        <div className="flex-between">
          <div>
            <h3>Active Clients</h3>
            <p className="text-secondary text-sm">Monitoring connection to Sesephus nodes.</p>
          </div>
          <button className="btn btn-primary">Refresh Clients</button>
        </div>
        
        <div className="mt-6">
          <div className="flex-between mb-4" style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
            <div className="flex-center gap-4">
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#4cd137' }}></div>
              <div>
                <div style={{ fontWeight: '600' }}>test-client</div>
                <div className="text-sm text-secondary">Local Machine</div>
              </div>
            </div>
            <div>
              <button className="btn">Trigger Record Alarm</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Circadia;
