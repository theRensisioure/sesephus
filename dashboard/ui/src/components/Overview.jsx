import React, { useState, useEffect } from 'react';

const Overview = () => {
  const [data, setData] = useState({ agents: {}, task_queue: [], artifacts: [] });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/dashboard');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to fetch overview data:", err);
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const agentsList = Object.values(data.agents || {});

  return (
    <div className="overview-module animate-fade-in">
      <h2>System Overview</h2>
      
      <div className="grid-3 mb-6">
        <div className="glass-panel stagger-1">
          <h3>Active Agents</h3>
          <div className="mt-4">
            {agentsList.length === 0 ? <p className="text-secondary">No agents online</p> : null}
            {agentsList.map(agent => (
              <div key={agent.name} className="flex-between mb-4">
                <div>
                  <div style={{ fontWeight: 600 }}>{agent.name}</div>
                  <div className="text-sm text-secondary">{agent.node}</div>
                </div>
                <span className={`badge ${agent.status === 'Idle' ? 'badge-success' : 'badge-warning'}`}>
                  {agent.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel stagger-2">
          <h3>Recent Tasks</h3>
          <div className="mt-4">
            {data.task_queue?.length === 0 ? <p className="text-secondary">Task queue empty</p> : null}
            {data.task_queue?.slice(0, 5).map(task => (
              <div key={task.id} className="mb-4">
                <div className="flex-between">
                  <span style={{fontWeight: 600}} className="text-accent">{task.domain}</span>
                  <span className="text-sm text-secondary">{new Date(task.created_at * 1000).toLocaleTimeString()}</span>
                </div>
                <div className="text-sm mt-2">{task.payload_summary}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel stagger-3">
          <h3>Artifacts</h3>
          <div className="mt-4">
            {data.artifacts?.length === 0 ? <p className="text-secondary">No artifacts</p> : null}
            {data.artifacts?.slice(0, 5).map(art => (
              <div key={art.id} className="mb-4">
                <div className="flex-between">
                  <span style={{fontWeight: 600}}>{art.type_name}</span>
                  <span className="text-sm text-secondary">{(art.size_bytes / 1024).toFixed(1)} KB</span>
                </div>
                <div className="text-sm mt-2 text-secondary">{art.file_path}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
