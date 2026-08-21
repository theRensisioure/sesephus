import React from 'react';
import { Link } from 'react-router-dom';
import shipments from '../data/shipments.json';

const STATUS_BADGE = {
  active: 'badge-success',
  loading: 'badge-warning',
  offline: 'badge-danger',
  docked: 'badge-info',
};

const ShipmentDock = () => {
  const activeCount = shipments.filter((s) => s.status === 'active').length;
  const sorted = [...shipments].sort((a, b) => (b.featured ? 1 : 0) - (a.featured ? 1 : 0));

  return (
    <div className="shipment-dock animate-fade-in">
      <div className="dock-header mb-6">
        <h2>Shipment Dock</h2>
        <p className="text-secondary mt-2">
          {activeCount} active shipment{activeCount !== 1 ? 's' : ''} on VisionOxide
        </p>
      </div>

      <div className="shipment-grid">
        {sorted.map((shipment, i) => (
          <div
            key={shipment.id}
            className={`shipment-card glass-panel ${shipment.featured ? 'shipment-card-featured' : ''} stagger-${(i % 3) + 1}`}
          >
            {shipment.featured && <span className="shipment-new-badge">NEW</span>}

            <div className="flex-between mb-4">
              <div className="shipment-card-title">
                <span className="shipment-icon">{shipment.icon}</span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{shipment.name}</div>
                  <div className="text-sm text-secondary">v{shipment.version}</div>
                </div>
              </div>
              <span className={`badge ${STATUS_BADGE[shipment.status] || 'badge-info'}`}>
                {shipment.status}
              </span>
            </div>

            <p className="text-sm text-secondary mb-4">{shipment.tagline}</p>

            {shipment.mission && (
              <p className="text-sm saturnnav-mission-card mb-4">{shipment.mission}</p>
            )}

            {shipment.modalities?.length > 0 && (
              <div className="modality-chips mb-4">
                {shipment.modalities.map((mod) => (
                  <span key={mod} className={`modality-chip ${mod === 'unicycle' ? 'modality-chip-primary' : ''}`}>
                    {mod === 'unicycle' ? '🎡 unicycle' : mod.replace('_', ' ')}
                  </span>
                ))}
              </div>
            )}

            {shipment.optimizers.length > 0 && (
              <div className="optimizer-chips mb-4">
                {shipment.optimizers.map((opt) => (
                  <span key={opt} className="optimizer-chip">{opt}</span>
                ))}
              </div>
            )}

            <div className="shipment-deps text-sm text-secondary mb-4">
              {shipment.dependencies.map((dep) => (
                <span key={dep} className="dep-chip">{dep}</span>
              ))}
            </div>

            <div className="shipment-card-actions gap-3">
              {shipment.id === 'saturnnav' ? (
                <Link to="/shipments/saturnnav/lab" className="btn btn-primary">Open Route Lab</Link>
              ) : shipment.status !== 'offline' ? (
                <Link to={`/shipments/${shipment.id}`} className="btn btn-primary">Enter Console</Link>
              ) : (
                <span className="btn" style={{ opacity: 0.5, cursor: 'not-allowed' }}>Offline</span>
              )}
              <Link to={`/shipments/${shipment.id}/manifest`} className="btn">Manifest</Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ShipmentDock;