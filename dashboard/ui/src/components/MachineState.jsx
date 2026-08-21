import React, { useState, useEffect } from 'react';

// Shape mirrors the /api/machine contract; used until the first poll lands
// and as the fallback for any keys a degraded backend omits.
const EMPTY_STATE = {
  subsystems: {},
  clients: [],
  alarms: [],
  agents: [],
  task_queue: [],
  artifacts: [],
  etdi: { trend: [], flag_count: 0 },
  last_updated: null,
};

const SUBSYSTEMS = [
  { key: 'dashboard_api', label: 'Dashboard API' },
  { key: 'zig_host', label: 'Zig Host' },
  { key: 'etdi_store', label: 'ETDI Store' },
];

function HealthDot({ ok }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        flexShrink: 0,
        background: ok ? 'var(--success-color)' : 'var(--danger-color)',
        boxShadow: ok
          ? '0 0 8px rgba(16, 185, 129, 0.6)'
          : '0 0 8px rgba(255, 107, 129, 0.6)',
      }}
    />
  );
}

function EtdiTrendBars({ trend }) {
  if (!trend.length) return <p className="text-secondary">No trend data</p>;
  const max = Math.max(...trend.map((t) => t.max_etdi), 0.01);
  const w = 18;
  const h = 60;
  return (
    <svg width={trend.length * w} height={h + 16} role="img" aria-label="ETDI 7-day trend">
      {trend.map((t, i) => {
        const avgH = (t.avg_etdi / max) * h;
        const maxH = (t.max_etdi / max) * h;
        return (
          <g key={t.day} transform={`translate(${i * w}, 0)`}>
            <rect x={3} y={h - maxH} width={w - 6} height={maxH} fill="rgba(124, 247, 255, 0.25)" rx={2} />
            <rect x={3} y={h - avgH} width={w - 6} height={avgH} fill="rgba(124, 247, 255, 0.85)" rx={2} />
            <title>{`${t.day} avg ${t.avg_etdi} max ${t.max_etdi} (${t.count} memos)`}</title>
          </g>
        );
      })}
      <text x={0} y={h + 12} fill="currentColor" fontSize="10" opacity="0.6">
        {trend[0].day} → {trend[trend.length - 1].day}
      </text>
    </svg>
  );
}

const MachineState = () => {
  const [data, setData] = useState(EMPTY_STATE);
  const [apiOffline, setApiOffline] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/machine');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        setApiOffline(false);
      } catch (err) {
        console.error('Failed to fetch machine state:', err);
        setApiOffline(true);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const subsystems = data.subsystems || {};
  const clients = data.clients || [];
  const alarms = data.alarms || [];
  const tasks = data.task_queue || [];
  const artifacts = data.artifacts || [];
  const etdi = data.etdi || EMPTY_STATE.etdi;
  const trend = etdi.trend || [];

  return (
    <div className="machine-state animate-fade-in">
      <div className="flex-between mb-4">
        <h2 style={{ marginBottom: 0 }}>Machine State</h2>
        {data.last_updated && (
          <span className="text-sm text-secondary">
            updated {new Date(data.last_updated).toLocaleTimeString()}
          </span>
        )}
      </div>

      {apiOffline && (
        <div
          className="glass-panel mb-6"
          style={{
            borderColor: 'var(--danger-color)',
            color: 'var(--danger-color)',
            padding: '12px 20px',
            fontFamily: "'JetBrains Mono', Menlo, Monaco, monospace",
            fontSize: '0.8rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          dashboard API offline — showing last known state
        </div>
      )}

      <div className="grid-3 mb-6">
        {SUBSYSTEMS.map(({ key, label }, i) => {
          const sub = subsystems[key];
          const ok = sub ? !!sub.ok : false;
          return (
            <div key={key} className={`glass-panel stagger-${i + 1}`}>
              <div className="flex-between">
                <h3 style={{ marginBottom: 0 }}>{label}</h3>
                <HealthDot ok={ok} />
              </div>
              <div className="text-sm text-secondary mt-2">
                {sub
                  ? sub.detail || (ok ? 'operational' : 'down')
                  : 'no status yet'}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid-2 mb-6">
        <div className="glass-panel">
          <h3>Clients</h3>
          <div className="mt-4">
            {clients.length === 0 ? <p className="text-secondary">No clients registered</p> : null}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                gap: 12,
              }}
            >
              {clients.map((client) => (
                <div key={client.client_id} className="glass-panel-sm flex-between">
                  <div>
                    <div style={{ fontWeight: 600 }}>{client.friendly_name}</div>
                    <div className="text-sm text-secondary">{client.client_id}</div>
                  </div>
                  <span className={`badge ${client.active ? 'badge-success' : 'badge-danger'}`}>
                    {client.active ? 'active' : 'idle'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-panel">
          <h3>Alarms</h3>
          <div className="mt-4">
            {alarms.length === 0 ? (
              <p className="text-secondary">No alarms set</p>
            ) : (
              <table style={{ width: '100%', fontSize: '0.85rem' }}>
                <thead>
                  <tr>
                    <th align="left">Trigger</th>
                    <th align="left">Action</th>
                    <th align="right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {alarms.map((alarm, i) => (
                    <tr key={alarm.id ?? i}>
                      <td>{String(alarm.trigger_time ?? '—')}</td>
                      <td>{String(alarm.action ?? '—')}</td>
                      <td align="right">
                        {alarm.fired ? (
                          <span className="badge badge-warning">fired</span>
                        ) : alarm.enabled ? (
                          <span className="badge badge-success">armed</span>
                        ) : (
                          <span className="badge badge-danger">off</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <div className="grid-3">
        <div className="glass-panel">
          <h3>Task Queue</h3>
          <div className="mt-4">
            {tasks.length === 0 ? <p className="text-secondary">Task queue empty</p> : null}
            {tasks.slice(0, 5).map((task) => (
              <div key={task.id} className="mb-4">
                <div className="flex-between">
                  <span style={{ fontWeight: 600 }} className="text-accent">{task.domain}</span>
                  <span className="text-sm text-secondary">
                    {new Date(task.created_at * 1000).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-sm mt-2">{task.payload_summary}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel">
          <h3>Artifacts</h3>
          <div className="mt-4">
            {artifacts.length === 0 ? <p className="text-secondary">No artifacts</p> : null}
            {artifacts.slice(0, 5).map((art) => (
              <div key={art.id} className="mb-4">
                <div className="flex-between">
                  <span style={{ fontWeight: 600 }}>{art.type_name}</span>
                  <span className="text-sm text-secondary">{(art.size_bytes / 1024).toFixed(1)} KB</span>
                </div>
                <div className="text-sm mt-2 text-secondary">{art.file_path}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel">
          <h3>ETDI · 7 Days</h3>
          <div className="mt-4">
            <EtdiTrendBars trend={trend} />
            <div className="text-sm text-secondary mt-4">
              <span className="text-accent" style={{ fontWeight: 600 }}>
                {etdi.flag_count ?? 0}
              </span>{' '}
              memo{(etdi.flag_count ?? 0) === 1 ? '' : 's'} above 0.30 threshold
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MachineState;
