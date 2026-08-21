export const MOCK_ORIGIN = { lat: 47.6062, lng: -122.3321, label: 'Origin' };
export const MOCK_DEST = { lat: 47.6205, lng: -122.3493, label: 'Destination' };

export const MOCK_ROUTES = [
  {
    id: 'route-a',
    label: 'Balanced',
    distance_km: 4.2,
    duration_min: 18,
    climb_m: 42,
    headwind_pct: 22,
    attribution: { altitude: 28, wind: 31, surface: 27, distance: 14 },
    geometry: [
      [47.6062, -122.3321], [47.6088, -122.3355], [47.6120, -122.3380],
      [47.6155, -122.3420], [47.6188, -122.3460], [47.6205, -122.3493],
    ],
  },
  {
    id: 'route-b',
    label: 'Flat Miler',
    distance_km: 4.8,
    duration_min: 20,
    climb_m: 18,
    headwind_pct: 35,
    attribution: { altitude: 52, wind: 18, surface: 20, distance: 10 },
    geometry: [
      [47.6062, -122.3321], [47.6075, -122.3380], [47.6100, -122.3430],
      [47.6140, -122.3470], [47.6180, -122.3485], [47.6205, -122.3493],
    ],
  },
  {
    id: 'route-c',
    label: 'Headwind Fighter',
    distance_km: 5.1,
    duration_min: 22,
    climb_m: 55,
    headwind_pct: 8,
    attribution: { altitude: 22, wind: 48, surface: 22, distance: 8 },
    geometry: [
      [47.6062, -122.3321], [47.6095, -122.3300], [47.6130, -122.3340],
      [47.6165, -122.3400], [47.6190, -122.3455], [47.6205, -122.3493],
    ],
  },
];

export const MOCK_BASINS = [
  {
    id: 'basin-1',
    center: { lat: 47.612, lng: -122.340 },
    radius_m: 600,
    polarity: 'repel',
    strength: 0.7,
  },
];