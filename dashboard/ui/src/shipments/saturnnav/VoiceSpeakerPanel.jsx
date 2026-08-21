import React, { useState } from 'react';
import {
  VOICE_SAMPLE_LINES,
  STIMULUS_LEVELS,
  STIMULUS_AVOIDS,
} from '../../data/riderProfiles';

const VoiceSpeakerPanel = ({ activeProfileName }) => {
  const [stimulusLevel, setStimulusLevel] = useState('whisper');
  const activeLevel = STIMULUS_LEVELS.find((l) => l.id === stimulusLevel);

  return (
    <div className="voice-speaker-panel mt-6">
      <h3>Speaker Layer</h3>
      <p className="text-sm text-secondary mt-2 mb-4">
        Low-stimulus by design — {activeProfileName} profile
      </p>

      <p className="stimulus-rationale text-sm mb-4">
        The road already has enough going on. SaturnNav keeps its side quiet so
        processing isn't fighting nav noise on top of everything else.
      </p>

      <div className="stimulus-level-row mb-4">
        <span className="text-sm">Stimulus budget</span>
        <div className="stimulus-level-btns">
          {STIMULUS_LEVELS.map((level) => (
            <button
              key={level.id}
              type="button"
              className={`preset-btn ${stimulusLevel === level.id ? 'active' : ''}`}
              onClick={() => setStimulusLevel(level.id)}
            >
              {level.label}
            </button>
          ))}
        </div>
      </div>

      {activeLevel && (
        <p className="text-sm text-secondary mb-4">{activeLevel.description}</p>
      )}

      <div className="voice-status flex-between mb-4">
        <span className="badge badge-info">{stimulusLevel}</span>
        <span className="text-sm text-secondary">limited understanding · on purpose</span>
      </div>

      <div className="voice-samples mb-4">
        {VOICE_SAMPLE_LINES.map((sample) => (
          <div key={sample.trigger} className="voice-line glass-panel-sm mb-2">
            <span className="voice-trigger text-sm text-secondary">{sample.trigger}</span>
            <p className="voice-utterance mt-2">{sample.line}</p>
          </div>
        ))}
      </div>

      <div className="stimulus-avoids">
        <span className="text-sm text-secondary">Won't do</span>
        <ul className="avoid-list mt-2">
          {STIMULUS_AVOIDS.map((item) => (
            <li key={item} className="text-sm">{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default VoiceSpeakerPanel;