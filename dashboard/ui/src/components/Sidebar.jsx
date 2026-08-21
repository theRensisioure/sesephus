import React from 'react';
import { NavLink } from 'react-router-dom';
import shipments from '../data/shipments.json';

const Sidebar = () => {
  const activeShipments = shipments.filter((s) => s.status === 'active' || s.status === 'loading');

  return (
    <div className="sidebar">
      <NavLink to="/" className="sidebar-logo">
        ⬡ <span>Sesephus</span>
      </NavLink>

      <div className="nav-section-label">Dock</div>
      <div className="nav-links">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} end>
          <span className="nav-icon">📦</span>
          Shipment Dock
        </NavLink>
        <NavLink to="/system" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">📊</span>
          System
        </NavLink>
        <NavLink to="/machine" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">🖥️</span>
          Machine State
        </NavLink>
        <NavLink to="/etdi" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon">⏳</span>
          ETDI
        </NavLink>
      </div>

      <div className="nav-section-label">Shipments</div>
      <div className="nav-links">
        {activeShipments.map((shipment) => (
          <NavLink
            key={shipment.id}
            to={shipment.id === 'saturnnav' ? '/shipments/saturnnav/lab' : `/shipments/${shipment.id}`}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{shipment.icon}</span>
            {shipment.name}
            {shipment.featured && <span className="nav-badge">new</span>}
          </NavLink>
        ))}
      </div>
    </div>
  );
};

export default Sidebar;