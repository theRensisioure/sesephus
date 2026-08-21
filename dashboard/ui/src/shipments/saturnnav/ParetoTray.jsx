import React from 'react';

const ParetoTray = ({ routes, activeRouteId, onSelect, activeRoute }) => {
  return (
    <div className="pareto-tray">
      <div className="pareto-routes">
        <h3 className="pareto-tray-title">Route Candidates</h3>
        <div className="pareto-list">
          {routes.map((route) => (
            <button
              key={route.id}
              type="button"
              className={`pareto-row ${activeRouteId === route.id ? 'pareto-row-active' : ''}`}
              onClick={() => onSelect(route.id)}
            >
              <div className="flex-between">
                <span style={{ fontWeight: 600 }}>{route.label}</span>
                <span className="text-sm text-accent">{route.distance_km} km</span>
              </div>
              <div className="pareto-stats text-sm text-secondary mt-2">
                <span>{route.duration_min} min</span>
                <span>↑ {route.climb_m}m</span>
                <span>wind {route.headwind_pct}%</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {activeRoute && (
        <div className="segment-breakdown">
          <h3 className="pareto-tray-title">Cost Attribution</h3>
          <div className="attribution-bars mt-4">
            {Object.entries(activeRoute.attribution).map(([key, pct]) => (
              <div key={key} className="attribution-row">
                <span className="text-sm" style={{ width: 70 }}>{key}</span>
                <div className="attribution-bar-track">
                  <div className="attribution-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-sm text-accent" style={{ width: 36 }}>{pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ParetoTray;