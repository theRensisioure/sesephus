import React from 'react';
import { WEIGHT_PRESETS, renormalizeWeights } from '../../utils/weights';

const OPTIMIZER_LABELS = {
  altitude: 'Altitude',
  wind: 'Wind Vector',
  surface: 'Surface',
  distance: 'Distance',
};

const OptimizationStack = ({ weights, onChange, activePreset, onPresetChange }) => {
  const handleSlider = (key, value) => {
    onChange(renormalizeWeights(weights, key, Number(value)));
    onPresetChange('Custom');
  };

  return (
    <div className="optimization-stack">
      <h3>Optimization Stack</h3>
      <p className="text-sm text-secondary mt-2 mb-4">Concurrent optimizers fused by weight</p>

      <div className="preset-row mb-4">
        {Object.keys(WEIGHT_PRESETS).map((preset) => (
          <button
            key={preset}
            type="button"
            className={`preset-btn ${activePreset === preset ? 'active' : ''}`}
            onClick={() => {
              onPresetChange(preset);
              onChange(
                Object.fromEntries(
                  Object.entries(WEIGHT_PRESETS[preset]).map(([k, v]) => [k, v * 100])
                )
              );
            }}
          >
            {preset}
          </button>
        ))}
      </div>

      {Object.entries(OPTIMIZER_LABELS).map(([key, label]) => (
        <div key={key} className="optimizer-slider-row">
          <div className="flex-between mb-2">
            <label htmlFor={`weight-${key}`} className="text-sm">{label}</label>
            <span className="text-sm text-accent">{Math.round(weights[key])}%</span>
          </div>
          <input
            id={`weight-${key}`}
            type="range"
            min="0"
            max="100"
            value={weights[key]}
            onChange={(e) => handleSlider(key, e.target.value)}
            className="optimizer-slider"
          />
        </div>
      ))}
    </div>
  );
};

export default OptimizationStack;