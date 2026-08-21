import React from 'react';
import { SESSION_PHASES } from '../../data/routeSession';

const SessionPhaseBar = ({ phase, onPhaseChange, isOffline, bundleReady }) => {
  return (
    <div className="session-phase-bar glass-panel mb-4">
      <div className="flex-between">
        <div className="phase-toggle">
          {Object.values(SESSION_PHASES).map((p) => (
            <button
              key={p.id}
              type="button"
              className={`phase-btn ${phase === p.id ? 'active' : ''}`}
              onClick={() => onPhaseChange(p.id)}
              disabled={p.id === 'inride' && !bundleReady}
              title={p.id === 'inride' && !bundleReady ? 'Complete preflight bundle first' : p.description}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="session-status flex-center gap-3">
          <span className={`badge ${isOffline ? 'badge-info' : 'badge-success'}`}>
            {isOffline ? 'offline · bundle ok' : 'online'}
          </span>
          {bundleReady && <span className="text-sm text-secondary">vault bundle ready</span>}
        </div>
      </div>
      <p className="text-sm text-secondary mt-3">{SESSION_PHASES[phase].description}</p>
    </div>
  );
};

export default SessionPhaseBar;