import React from 'react';
import { RIDER_PROFILES } from '../../data/riderProfiles';

const RiderProfileSelector = ({ activeProfileId, onSelect }) => {
  return (
    <div className="rider-profile-selector">
      <h3>Rider Profile</h3>
      <p className="text-sm text-secondary mt-2 mb-4">
        Modality shapes the optimization stack
      </p>

      <div className="profile-grid">
        {RIDER_PROFILES.map((profile) => (
          <button
            key={profile.id}
            type="button"
            className={`profile-card ${activeProfileId === profile.id ? 'profile-card-active' : ''} ${profile.featured ? 'profile-card-featured' : ''}`}
            onClick={() => onSelect(profile.id)}
          >
            {profile.featured && <span className="profile-priority-badge">especially</span>}
            <span className="profile-icon">{profile.icon}</span>
            <span className="profile-name">{profile.name}</span>
          </button>
        ))}
      </div>

      {RIDER_PROFILES.filter((p) => p.id === activeProfileId).map((profile) => (
        <div key={profile.id} className="profile-detail mt-4">
          <p className="text-sm text-secondary">{profile.tagline}</p>
          <div className="hint-chips mt-2">
            {profile.hints.map((hint) => (
              <span key={hint} className="hint-chip">{hint}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default RiderProfileSelector;