import React from 'react';
import { Link, useParams } from 'react-router-dom';
import Circadia from '../components/Circadia';
import Arcadium from '../components/Arcadium';
import Sieve from '../components/Sieve';
import shipments from '../data/shipments.json';

const CONSOLES = {
  circadia: Circadia,
  arcadium: Arcadium,
  sieve: Sieve,
};

const ShipmentConsole = () => {
  const { id } = useParams();
  const shipment = shipments.find((s) => s.id === id);
  const Console = CONSOLES[id];

  if (!shipment) {
    return (
      <div className="animate-fade-in">
        <h2>Shipment Not Found</h2>
        <Link to="/" className="btn mt-4">Back to Dock</Link>
      </div>
    );
  }

  if (!Console) {
    return (
      <div className="animate-fade-in">
        <h2>{shipment.name}</h2>
        <p className="text-secondary mt-4">Console not available for this shipment.</p>
        <Link to="/" className="btn mt-4">Back to Dock</Link>
      </div>
    );
  }

  return (
    <div className="shipment-console animate-fade-in">
      <div className="console-header flex-between mb-4">
        <div>
          <span className="text-sm text-secondary">Shipment</span>
          <h2>{shipment.icon} {shipment.name} <span className="text-accent text-sm">v{shipment.version}</span></h2>
        </div>
        <Link to={`/shipments/${id}/manifest`} className="btn">Manifest</Link>
      </div>
      <Console />
    </div>
  );
};

export default ShipmentConsole;