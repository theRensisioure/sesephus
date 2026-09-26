import React, { useState } from 'react';

const Arcadium = () => {
  const [transcription, setTranscription] = useState('');
  const [loading, setLoading] = useState(false);
  const [client, setClient] = useState('test-client');
  const [wavPath, setWavPath] = useState('recordings/journal_test.wav');

  const handleTranscribe = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: client, wav_path: wavPath })
      });
      const data = await res.json();
      setTranscription(data.text);
    } catch (err) {
      console.error(err);
      setTranscription("Failed to transcribe.");
    }
    setLoading(false);
  };

  return (
    <div className="arcadium-module animate-fade-in">
      <h2>Arcadium Audio Journaling</h2>
      <p className="text-sm text-secondary">Retained dashboard face. Current Voice is external Clippers at C:\dev\journal-clippers\audio-journal-system. This panel is not the recorder.</p>
      
      <div className="grid-2 mt-6">
        <div className="glass-panel">
          <h3>Manual Transcription Trigger</h3>
          <div className="mt-4">
            <div className="mb-4">
              <label className="text-sm text-secondary block mb-2">Client ID</label>
              <input 
                type="text" 
                value={client} 
                onChange={e => setClient(e.target.value)}
                style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '4px' }}
              />
            </div>
            <div className="mb-4">
              <label className="text-sm text-secondary block mb-2">WAV Path</label>
              <input 
                type="text" 
                value={wavPath} 
                onChange={e => setWavPath(e.target.value)}
                style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--panel-border)', color: '#fff', borderRadius: '4px' }}
              />
            </div>
            <button className="btn btn-primary mt-4" onClick={handleTranscribe} disabled={loading}>
              {loading ? 'Transcribing...' : 'Run Transcription'}
            </button>
          </div>
        </div>

        <div className="glass-panel">
          <h3>Transcription Result</h3>
          <div className="mt-4" style={{ minHeight: '150px', padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
            {transcription || <span className="text-secondary italic">No transcription to show.</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Arcadium;
