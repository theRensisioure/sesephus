export const DEFAULT_WEIGHTS = {
  altitude: 0.35,
  wind: 0.30,
  surface: 0.20,
  distance: 0.15,
};

export const WEIGHT_PRESETS = {
  FlatMiler: { altitude: 0.55, wind: 0.15, surface: 0.15, distance: 0.15 },
  HeadwindFighter: { altitude: 0.15, wind: 0.55, surface: 0.15, distance: 0.15 },
  ClimbAvoider: { altitude: 0.60, wind: 0.10, surface: 0.20, distance: 0.10 },
  Balanced: { altitude: 0.25, wind: 0.25, surface: 0.25, distance: 0.25 },
};

export function renormalizeWeights(weights, changedKey, newValue) {
  const clamped = Math.max(0, Math.min(100, newValue));
  const remaining = 100 - clamped;
  const others = Object.keys(weights).filter((k) => k !== changedKey);
  const otherSum = others.reduce((sum, k) => sum + weights[k], 0);

  const next = { ...weights, [changedKey]: clamped };
  if (otherSum === 0) {
    const share = remaining / others.length;
    others.forEach((k) => { next[k] = share; });
  } else {
    others.forEach((k) => {
      next[k] = (weights[k] / otherSum) * remaining;
    });
  }
  return next;
}

export function toNormalized(weights) {
  const sum = Object.values(weights).reduce((a, b) => a + b, 0);
  if (sum === 0) return { ...DEFAULT_WEIGHTS };
  return Object.fromEntries(
    Object.entries(weights).map(([k, v]) => [k, v / sum])
  );
}