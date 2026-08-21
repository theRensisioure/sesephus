import React, { useMemo } from 'react';

const VIEW = { minLat: 47.602, maxLat: 47.624, minLng: -122.355, maxLng: -122.326 };

function project(lat, lng, width, height) {
  const x = ((lng - VIEW.minLng) / (VIEW.maxLng - VIEW.minLng)) * width;
  const y = ((VIEW.maxLat - lat) / (VIEW.maxLat - VIEW.minLat)) * height;
  return { x, y };
}

function toPath(geometry, width, height) {
  return geometry
    .map(([lat, lng], i) => {
      const { x, y } = project(lat, lng, width, height);
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}

const RouteMap = ({
  routes,
  activeRouteId,
  origin,
  destination,
  basins,
  onMapClick,
  placingMode,
}) => {
  const width = 800;
  const height = 480;

  const activeRoute = routes.find((r) => r.id === activeRouteId) || routes[0];

  const basinCircles = useMemo(
    () => basins.map((basin) => {
      const { x, y } = project(basin.center.lat, basin.center.lng, width, height);
      const r = (basin.radius_m / 5000) * width * 0.4;
      return { ...basin, cx: x, cy: y, r: Math.max(20, r) };
    }),
    [basins, width, height]
  );

  const handleClick = (e) => {
    if (!placingMode || !onMapClick) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const lng = VIEW.minLng + (x / width) * (VIEW.maxLng - VIEW.minLng);
    const lat = VIEW.maxLat - (y / height) * (VIEW.maxLat - VIEW.minLat);
    onMapClick({ lat, lng });
  };

  const originPt = project(origin.lat, origin.lng, width, height);
  const destPt = project(destination.lat, destination.lng, width, height);

  return (
    <div
      className={`route-map ${placingMode ? 'route-map-placing' : ''}`}
      onClick={handleClick}
      role="presentation"
    >
      <svg viewBox={`0 0 ${width} ${height}`} className="route-map-svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(124,247,255,0.06)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#grid)" />
        <rect width={width} height={height} fill="rgba(6,6,8,0.6)" />

        {basinCircles.map((basin) => (
          <circle
            key={basin.id}
            cx={basin.cx}
            cy={basin.cy}
            r={basin.r}
            className={`basin-overlay basin-${basin.polarity}`}
            opacity={basin.strength * 0.5}
          />
        ))}

        {routes.filter((r) => r.id !== activeRouteId).map((route) => (
          <path
            key={route.id}
            d={toPath(route.geometry, width, height)}
            className="route-line route-line-inactive"
            fill="none"
          />
        ))}

        {activeRoute && (
          <path
            d={toPath(activeRoute.geometry, width, height)}
            className="route-line route-line-active"
            fill="none"
          />
        )}

        <circle cx={originPt.x} cy={originPt.y} r={8} className="map-pin map-pin-origin" />
        <text x={originPt.x + 12} y={originPt.y + 4} className="map-label">{origin.label}</text>

        <circle cx={destPt.x} cy={destPt.y} r={8} className="map-pin map-pin-dest" />
        <text x={destPt.x + 12} y={destPt.y + 4} className="map-label">{destination.label}</text>
      </svg>

      {placingMode && (
        <div className="route-map-hint">Click to place basin center</div>
      )}
    </div>
  );
};

export default RouteMap;