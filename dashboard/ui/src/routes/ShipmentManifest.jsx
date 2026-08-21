import React from 'react';
import { Link, useParams } from 'react-router-dom';
import shipments from '../data/shipments.json';

const ShipmentManifest = () => {
  const { id } = useParams();
  const shipment = shipments.find((s) => s.id === id);

  if (!shipment) {
    return (
      <div className="animate-fade-in">
        <h2>Shipment Not Found</h2>
        <Link to="/" className="btn mt-4">Back to Dock</Link>
      </div>
    );
  }

  return (
    <div className="shipment-manifest animate-fade-in">
      <div className="flex-between mb-6">
        <div>
          <h2>{shipment.icon} {shipment.name} Manifest</h2>
          <p className="text-secondary mt-2">v{shipment.version}</p>
        </div>
        <Link to="/" className="btn">← Dock</Link>
      </div>

      {shipment.mission && (
        <div className="glass-panel mb-6 saturnnav-mission-panel">
          <h3>Mission</h3>
          <p className="text-secondary mt-4">{shipment.mission}</p>
        </div>
      )}

      <div className="grid-2">
        <div className="glass-panel">
          <h3>Cargo</h3>
          <p className="text-secondary mt-4">{shipment.tagline}</p>
          {shipment.modalities?.length > 0 && (
            <div className="modality-chips mt-4">
              {shipment.modalities.map((mod) => (
                <span key={mod} className={`modality-chip ${mod === 'unicycle' ? 'modality-chip-primary' : ''}`}>
                  {mod === 'unicycle' ? '🎡 unicycle (especially)' : mod.replace('_', ' ')}
                </span>
              ))}
            </div>
          )}
          <ul className="manifest-list mt-4">
            {shipment.scope_in.map((item) => (
              <li key={item} className="text-sm">{item}</li>
            ))}
          </ul>
        </div>

        <div className="glass-panel">
          <h3>Dependencies</h3>
          <ul className="manifest-list mt-4">
            {shipment.dependencies.map((dep) => (
              <li key={dep} className="text-sm text-accent">{dep}</li>
            ))}
          </ul>
        </div>

        <div className="glass-panel">
          <h3>In Scope (v{shipment.version})</h3>
          <ul className="manifest-list mt-4">
            {shipment.scope_in.map((item) => (
              <li key={`in-${item}`} className="text-sm text-success">{item}</li>
            ))}
          </ul>
        </div>

        <div className="glass-panel">
          <h3>Not In Scope</h3>
          <ul className="manifest-list mt-4">
            {shipment.scope_out.map((item) => (
              <li key={item} className="text-sm text-secondary">{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="glass-panel mt-6">
        <h3>Changelog</h3>
        <ul className="manifest-list mt-4">
          {shipment.changelog.map((entry) => (
            <li key={entry} className="text-sm">{entry}</li>
          ))}
        </ul>
      </div>

      {shipment.id === 'saturnnav' && (
        <div className="mt-6">
          <Link to="/shipments/saturnnav/lab" className="btn btn-primary">Open Route Lab</Link>
        </div>
      )}
      {shipment.id !== 'saturnnav' && shipment.status !== 'offline' && (
        <div className="mt-6">
          <Link to={`/shipments/${shipment.id}`} className="btn btn-primary">Enter Console</Link>
        </div>
      )}
    </div>
  );
};

export default ShipmentManifest;