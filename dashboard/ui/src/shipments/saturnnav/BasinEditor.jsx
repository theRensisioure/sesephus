import React from 'react';

const BasinEditor = ({ basins, onAdd, onRemove, onTogglePolarity, placingMode, onStartPlace }) => {
  return (
    <div className="basin-editor mt-6">
      <h3>Attractor Basins</h3>
      <p className="text-sm text-secondary mt-2 mb-4">Define preference zones on the map</p>

      <button
        type="button"
        className={`btn btn-sm mb-4 ${placingMode ? 'btn-primary' : ''}`}
        onClick={onStartPlace}
      >
        {placingMode ? 'Click map to place…' : '+ Add Basin'}
      </button>

      <div className="basin-list">
        {basins.length === 0 && (
          <p className="text-sm text-secondary">No basins defined</p>
        )}
        {basins.map((basin) => (
          <div key={basin.id} className="basin-item glass-panel-sm mb-2">
            <div className="flex-between">
              <span className={`basin-polarity ${basin.polarity}`}>
                {basin.polarity === 'attract' ? '⊕ Attract' : '⊖ Repel'}
              </span>
              <button type="button" className="btn-icon" onClick={() => onRemove(basin.id)}>×</button>
            </div>
            <div className="text-sm text-secondary mt-2">
              r={basin.radius_m}m · strength {basin.strength}
            </div>
            <button
              type="button"
              className="btn btn-sm mt-2"
              onClick={() => onTogglePolarity(basin.id)}
            >
              Flip polarity
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default BasinEditor;