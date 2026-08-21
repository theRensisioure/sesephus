export const SESSION_PHASES = {
  preflight: {
    id: 'preflight',
    label: 'Preflight',
    description: 'Heavy processing happens here — graph, wind snapshot, Pareto set, speaker script.',
  },
  inride: {
    id: 'inride',
    label: 'In-Ride',
    description: 'Light edits only. No full reroute. Works offline from the preflight bundle.',
  },
};

export const PREFLIGHT_STEPS = [
  { id: 'graph', label: 'OSM graph + bike edges', requiresNetwork: false },
  { id: 'dem', label: 'DEM elevation tiles', requiresNetwork: false },
  { id: 'wind', label: 'Wind snapshot at depart_at', requiresNetwork: true },
  { id: 'pareto', label: 'Pareto route candidates', requiresNetwork: false },
  { id: 'speaker', label: 'Sparse speaker script', requiresNetwork: false },
  { id: 'bundle', label: 'Session bundle → local vault', requiresNetwork: false },
];

export const INRIDE_EDIT_RULES = {
  allowed: [
    'Switch among preflight Pareto candidates',
    'Nudge optimizer weights (maps to cached alternates)',
    'Adjust stimulus budget',
    'Flip basin polarity on cached geometry',
  ],
  blocked: [
    'Full A* reroute from current position',
    'New origin / destination',
    'Add basins that require network fetch',
    'Live wind refresh',
  ],
};

export const OFFLINE_GUARANTEES = [
  'Active route never dropped — last good polyline stays until a cached alternate applies',
  'Edits patch within the preflight corridor, not a blank recalc',
  'No "routing lost" screen — graceful keep-current on failed patch',
  'Cellular optional after bundle is written',
];

export const MOCK_PREFLIGHT_STATUS = {
  graph: 'ready',
  dem: 'ready',
  wind: 'snapshotted',
  pareto: 'ready',
  speaker: 'ready',
  bundle: 'pending',
};

export function applyInRideWeightNudge(routes, weights) {
  const alt = Math.round(weights.altitude);
  const wind = Math.round(weights.wind);
  if (alt >= 50) return 'route-b';
  if (wind >= 45) return 'route-c';
  return 'route-a';
}