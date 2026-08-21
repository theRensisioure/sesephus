import React, { useEffect, useState } from 'react';

// Relative paths ride the Vite dev proxy (vite.config.js forwards /api to the
// sidecar on :3001), so the page works from any device that can reach the UI.
const API = '';

function TrendBars({ trend }) {
  if (!trend.length) return <p className="etdi-empty">No scored memos yet. Run tools/etdi_pipeline.py.</p>;
  const max = Math.max(...trend.map((t) => t.max_etdi), 0.01);
  const w = 18;
  const h = 90;
  return (
    <svg width={trend.length * w} height={h + 20} role="img" aria-label="Daily ETDI trend">
      {trend.map((t, i) => {
        const avgH = (t.avg_etdi / max) * h;
        const maxH = (t.max_etdi / max) * h;
        return (
          <g key={t.day} transform={`translate(${i * w}, 0)`}>
            <rect x={3} y={h - maxH} width={w - 6} height={maxH} fill="rgba(120,140,255,0.25)" rx={2} />
            <rect x={3} y={h - avgH} width={w - 6} height={avgH} fill="rgba(120,140,255,0.85)" rx={2} />
            <title>{`${t.day} avg ${t.avg_etdi} max ${t.max_etdi} (${t.count} memos)`}</title>
          </g>
        );
      })}
      <text x={0} y={h + 14} fill="currentColor" fontSize="10" opacity="0.6">
        {trend[0].day} → {trend[trend.length - 1].day}
      </text>
    </svg>
  );
}

const EtdiPanel = () => {
  const [trend, setTrend] = useState([]);
  const [flags, setFlags] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/etdi/trend`).then((r) => r.json()),
      fetch(`${API}/api/etdi/flags`).then((r) => r.json()),
    ])
      .then(([t, f]) => {
        setTrend(t.trend || []);
        setFlags(f.flags || []);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="etdi-panel">
      <h2>Emotional Time Density (ETDI)</h2>
      <p style={{ opacity: 0.7 }}>
        √(valence² + arousal² + salience²) / (√3 × duration_minutes) — higher means denser
        emotional signal per minute, a candidate for subjective time distortion. Flag
        threshold 0.30; a one-minute memo tops out at 1.0.
      </p>

      {error && <p style={{ color: 'salmon' }}>Dashboard server unreachable: {error}</p>}

      <h3>Daily trend</h3>
      <TrendBars trend={trend} />

      <h3>High-density flags</h3>
      {flags.length === 0 ? (
        <p className="etdi-empty">No memos above threshold.</p>
      ) : (
        <table style={{ width: '100%', fontSize: '0.85rem' }}>
          <thead>
            <tr>
              <th align="left">Entry</th>
              <th align="left">When</th>
              <th align="right">ETDI</th>
              <th align="left">Emotion</th>
              <th align="right">Distortion</th>
              <th align="left">Rationale</th>
            </tr>
          </thead>
          <tbody>
            {flags.map((f) => (
              <tr key={f.entry_id}>
                <td>{f.entry_id}</td>
                <td>{(f.recorded_at_utc || '').slice(0, 10)}</td>
                <td align="right">{f.etdi}</td>
                <td>{f.primary_emotion}</td>
                <td align="right">{f.time_distortion_likelihood}</td>
                <td style={{ opacity: 0.7 }}>{f.rationale}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default EtdiPanel;
