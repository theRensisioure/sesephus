import React, { useState, useEffect, useRef } from 'react';

const Circadia = () => {
  const [activeTab, setActiveTab] = useState('single');
  const [clients, setClients] = useState([]);
  const [subgroups, setSubgroups] = useState([]);
  const [alarms, setAlarms] = useState([]);
  const [selectedAlarms, setSelectedAlarms] = useState([]);
  const [connected, setConnected] = useState(false);

  // Forms
  const [singleAlarm, setSingleAlarm] = useState({
    seconds: 5,
    action: 'play_sound',
    duration: 1.0,
    targetType: 'client', // 'client' or 'group'
    targetId: ''
  });

  const [intervalAlarm, setIntervalAlarm] = useState({
    duration_sec: 10,
    count: 4,
    action: 'play_sound',
    action_duration: 1.0,
    targetType: 'client', // 'client' or 'group'
    targetId: ''
  });

  const [newGroup, setNewGroup] = useState({
    name: '',
    client_ids: []
  });

  const [tuning, setTuning] = useState({
    parent_id: '',
    spacing_sec: 5.0,
    jitter_ms: 0
  });

  // Poll server for status
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch('http://127.0.0.1:3000/api/status');
        if (!res.ok) throw new Error('Not OK');
        const data = await res.json();
        if (active) {
          setClients(data.clients || []);
          setAlarms(data.alarms || []);
          setSubgroups(data.subgroups || []);
          setConnected(true);
        }
      } catch (err) {
        if (active) {
          setConnected(false);
        }
      }
    };
    poll();
    const interval = setInterval(poll, 1500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Set default targets once clients/subgroups load
  useEffect(() => {
    if (clients.length > 0 && !singleAlarm.targetId) {
      setSingleAlarm(prev => ({ ...prev, targetId: clients[0].client_id }));
    }
    if (clients.length > 0 && !intervalAlarm.targetId) {
      setIntervalAlarm(prev => ({ ...prev, targetId: clients[0].client_id }));
    }
  }, [clients]);

  // Keep Precision Tuning pointed at a live interval parent as alarms fire / refresh
  useEffect(() => {
    const parents = [...new Set(
      alarms.filter(a => a.parent_id && !a.fired).map(a => a.parent_id)
    )];
    if (parents.length === 0) {
      if (tuning.parent_id) setTuning(p => ({ ...p, parent_id: '' }));
      return;
    }
    if (!parents.includes(tuning.parent_id)) {
      setTuning(p => ({ ...p, parent_id: parents[0] }));
    }
  }, [alarms]);

  // Actions
  const handleCreateSingle = async (e) => {
    e.preventDefault();
    const payload = {
      seconds: parseInt(singleAlarm.seconds),
      action: singleAlarm.action,
      duration: parseFloat(singleAlarm.duration)
    };
    if (singleAlarm.targetType === 'group') {
      payload.group_id = singleAlarm.targetId;
    } else {
      payload.client_id = singleAlarm.targetId;
    }

    try {
      const res = await fetch('http://127.0.0.1:3000/api/alarm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        alert("Alarm scheduled successfully!");
      } else {
        alert("Failed to schedule: " + (data.message || "Unknown error"));
      }
    } catch (err) {
      alert("Host daemon unreachable — alarm was NOT scheduled.");
    }
  };

  const handleCreateInterval = async (e) => {
    e.preventDefault();
    const payload = {
      duration_sec: parseInt(intervalAlarm.duration_sec),
      count: parseInt(intervalAlarm.count),
      action: intervalAlarm.action,
      action_duration: parseFloat(intervalAlarm.action_duration)
    };
    if (intervalAlarm.targetType === 'group') {
      payload.group_id = intervalAlarm.targetId;
    } else {
      payload.client_ids = [intervalAlarm.targetId];
    }

    try {
      const res = await fetch('http://127.0.0.1:3000/api/alarm/create_interval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        alert(`Interval sequence created! Parent ID: ${data.parent_id}`);
      } else {
        alert("Failed to create: " + (data.message || "Unknown error"));
      }
    } catch (err) {
      alert("Host daemon unreachable — interval sequence was NOT created.");
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroup.name) return;
    try {
      const res = await fetch('http://127.0.0.1:3000/api/group', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newGroup.name,
          client_ids: newGroup.client_ids
        })
      });
      const data = await res.json();
      if (data.success) {
        setNewGroup({ name: '', client_ids: [] });
      }
    } catch (err) {
      alert("Host daemon unreachable — group was NOT created.");
    }
  };

  const handleDeleteGroup = async (groupId) => {
    try {
      await fetch('http://127.0.0.1:3000/api/group/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId })
      });
    } catch (err) {
      alert("Host daemon unreachable — group was NOT deleted.");
    }
  };

  const handleAdjustInterval = async (e) => {
    e.preventDefault();
    if (!tuning.parent_id) return;
    try {
      const res = await fetch('http://127.0.0.1:3000/api/alarm/adjust_interval', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parent_id: tuning.parent_id,
          spacing_sec: parseFloat(tuning.spacing_sec),
          jitter_ms: parseInt(tuning.jitter_ms) || null
        })
      });
      const data = await res.json();
      if (data.success) {
        alert("Interval sequence adjusted!");
      }
    } catch (err) {
      alert("Host daemon unreachable — interval was NOT adjusted.");
    }
  };

  // Bulk Edit
  const handleBulkEdit = async (enabled) => {
    if (selectedAlarms.length === 0) return;
    try {
      await fetch('http://127.0.0.1:3000/api/alarm/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alarm_ids: selectedAlarms,
          enabled: enabled
        })
      });
    } catch (err) {
      alert("Host daemon unreachable — alarms were NOT edited.");
    }
  };

  const handleToggleAll = async (enabled) => {
    try {
      await fetch('http://127.0.0.1:3000/api/alarm/toggle_all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
    } catch (err) {
      alert("Host daemon unreachable — alarms were NOT toggled.");
    }
  };

  const toggleSelectAlarm = (id) => {
    setSelectedAlarms(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAllAlarms = () => {
    const activeAlarms = alarms.filter(a => !a.fired).map(a => a.alarm_id);
    if (selectedAlarms.length === activeAlarms.length) {
      setSelectedAlarms([]);
    } else {
      setSelectedAlarms(activeAlarms);
    }
  };

  // Helper to resolve client names for list display
  const getClientNames = (clientIds) => {
    if (!clientIds || clientIds.length === 0) return 'None';
    return clientIds.map(cid => {
      const found = clients.find(c => c.client_id === cid);
      return found ? found.friendly_name : cid;
    }).join(', ');
  };

  // Unique parent IDs from still-pending interval alarms (for Precision Tuning)
  const activeParentIds = [...new Set(
    alarms.filter(a => a.parent_id && !a.fired).map(a => a.parent_id)
  )];

  return (
    <div className="circadia-module animate-fade-in" style={{ color: '#f3f4f6' }}>
      <div className="flex-between">
        <h2>Circadia Alarm Engine</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ 
            width: '10px', 
            height: '10px', 
            borderRadius: '50%', 
            background: connected ? '#10b981' : '#ef4444',
            boxShadow: connected ? '0 0 8px #10b981' : '0 0 8px #ef4444'
          }}></span>
          <span style={{ fontSize: '14px', color: '#9ca3af' }}>
            {connected ? 'Syncing to Host Daemon' : 'Host daemon unreachable (127.0.0.1:3000) — no live data'}
          </span>
        </div>
      </div>

      <div className="grid-2 mt-6">
        {/* Left Column: Devices and Subgroups */}
        <div>
          <div className="glass-panel mb-6">
            <h3>Connected Devices</h3>
            <p className="text-secondary text-sm mb-4">Win32 TCP listeners online.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {clients.map(c => (
                <div key={c.client_id} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '12px', 
                  background: 'rgba(0,0,0,0.15)', 
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.03)'
                }}>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '15px' }}>{c.friendly_name}</div>
                    <div className="text-sm text-secondary">{c.client_id}</div>
                  </div>
                  <span style={{
                    alignSelf: 'center',
                    padding: '2px 8px',
                    fontSize: '11px',
                    borderRadius: '12px',
                    background: c.active ? 'rgba(16,185,129,0.2)' : 'rgba(156,163,175,0.2)',
                    color: c.active ? '#34d399' : '#9ca3af'
                  }}>{c.active ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
              ))}
              {clients.length === 0 && <div className="text-secondary italic text-sm">No devices connected.</div>}
            </div>
          </div>

          <div className="glass-panel">
            <h3>Subgroups Administration</h3>
            <p className="text-secondary text-sm mb-4">Administer clients in groups.</p>
            
            <form onSubmit={handleCreateGroup} style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <input 
                  type="text" 
                  placeholder="Subgroup Name (e.g. Subgroup-A)" 
                  value={newGroup.name}
                  onChange={e => setNewGroup(p => ({ ...p, name: e.target.value }))}
                  style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                />
                
                <div style={{ fontSize: '13px', color: '#9ca3af' }}>Select Member Clients:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', padding: '8px 0' }}>
                  {clients.map(c => {
                    const isChecked = newGroup.client_ids.includes(c.client_id);
                    return (
                      <label key={c.client_id} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                        <input 
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            setNewGroup(prev => {
                              const cids = isChecked 
                                ? prev.client_ids.filter(id => id !== c.client_id) 
                                : [...prev.client_ids, c.client_id];
                              return { ...prev, client_ids: cids };
                            });
                          }}
                        />
                        {c.friendly_name}
                      </label>
                    );
                  })}
                </div>
                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>Create Subgroup</button>
              </div>
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {subgroups.map(g => (
                <div key={g.group_id} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  padding: '12px', 
                  background: 'rgba(0,0,0,0.15)', 
                  borderRadius: '6px',
                  border: '1px solid rgba(255,255,255,0.03)'
                }}>
                  <div>
                    <div style={{ fontWeight: '600' }}>{g.name}</div>
                    <div className="text-sm text-secondary" style={{ fontSize: '12px' }}>
                      IDs: {g.client_ids.join(', ') || 'No members'}
                    </div>
                  </div>
                  <button onClick={() => handleDeleteGroup(g.group_id)} style={{
                    background: 'rgba(239,68,68,0.2)',
                    color: '#f87171',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}>Delete</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Schedulers & Precision Tuning */}
        <div>
          <div className="glass-panel">
            <div className="tabs-header" style={{ display: 'flex', gap: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px', marginBottom: '16px' }}>
              <button 
                className={`tab-btn ${activeTab === 'single' ? 'active' : ''}`} 
                onClick={() => setActiveTab('single')}
                style={{ background: 'none', border: 'none', color: activeTab === 'single' ? '#818cf8' : '#9ca3af', borderBottom: activeTab === 'single' ? '2px solid #818cf8' : 'none', padding: '4px 8px', cursor: 'pointer', fontWeight: '600' }}
              >Single Alarm</button>
              <button 
                className={`tab-btn ${activeTab === 'interval' ? 'active' : ''}`} 
                onClick={() => setActiveTab('interval')}
                style={{ background: 'none', border: 'none', color: activeTab === 'interval' ? '#818cf8' : '#9ca3af', borderBottom: activeTab === 'interval' ? '2px solid #818cf8' : 'none', padding: '4px 8px', cursor: 'pointer', fontWeight: '600' }}
              >Interval Creator</button>
              <button 
                className={`tab-btn ${activeTab === 'tuning' ? 'active' : ''}`} 
                onClick={() => setActiveTab('tuning')}
                style={{ background: 'none', border: 'none', color: activeTab === 'tuning' ? '#818cf8' : '#9ca3af', borderBottom: activeTab === 'tuning' ? '2px solid #818cf8' : 'none', padding: '4px 8px', cursor: 'pointer', fontWeight: '600' }}
              >Precision Tuning</button>
            </div>

            {activeTab === 'single' && (
              <form onSubmit={handleCreateSingle}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="single-target" 
                        checked={singleAlarm.targetType === 'client'}
                        onChange={() => setSingleAlarm(p => ({ ...p, targetType: 'client', targetId: clients[0]?.client_id || '' }))}
                      />
                      Client Device
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="single-target" 
                        checked={singleAlarm.targetType === 'group'}
                        onChange={() => setSingleAlarm(p => ({ ...p, targetType: 'group', targetId: subgroups[0]?.group_id || '' }))}
                      />
                      Subgroup Target
                    </label>
                  </div>

                  <div>
                    <label className="text-secondary text-sm block mb-1">Target ID</label>
                    <select 
                      value={singleAlarm.targetId}
                      onChange={e => setSingleAlarm(p => ({ ...p, targetId: e.target.value }))}
                      style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    >
                      {singleAlarm.targetType === 'client' 
                        ? clients.map(c => <option key={c.client_id} value={c.client_id}>{c.friendly_name}</option>)
                        : subgroups.map(g => <option key={g.group_id} value={g.group_id}>{g.name}</option>)
                      }
                      {((singleAlarm.targetType === 'client' ? clients.length : subgroups.length) === 0) && <option value="">-- No Targets Available --</option>}
                    </select>
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Trigger (Seconds)</label>
                      <input 
                        type="number" 
                        value={singleAlarm.seconds}
                        onChange={e => setSingleAlarm(p => ({ ...p, seconds: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Action Duration (Sec)</label>
                      <input 
                        type="number" 
                        step="0.1"
                        value={singleAlarm.duration}
                        onChange={e => setSingleAlarm(p => ({ ...p, duration: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-secondary text-sm block mb-1">Action Mode</label>
                    <select 
                      value={singleAlarm.action}
                      onChange={e => setSingleAlarm(p => ({ ...p, action: e.target.value }))}
                      style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    >
                      <option value="play_sound">Play Sound (Beep)</option>
                      <option value="record_audio">Record Audio Journal</option>
                      <option value="run_command">Run Client Command</option>
                    </select>
                  </div>

                  <button type="submit" className="btn btn-primary mt-2">Schedule Alarm</button>
                </div>
              </form>
            )}

            {activeTab === 'interval' && (
              <form onSubmit={handleCreateInterval}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="int-target" 
                        checked={intervalAlarm.targetType === 'client'}
                        onChange={() => setIntervalAlarm(p => ({ ...p, targetType: 'client', targetId: clients[0]?.client_id || '' }))}
                      />
                      Client Device
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="int-target" 
                        checked={intervalAlarm.targetType === 'group'}
                        onChange={() => setIntervalAlarm(p => ({ ...p, targetType: 'group', targetId: subgroups[0]?.group_id || '' }))}
                      />
                      Subgroup Target
                    </label>
                  </div>

                  <div>
                    <label className="text-secondary text-sm block mb-1">Target ID</label>
                    <select 
                      value={intervalAlarm.targetId}
                      onChange={e => setIntervalAlarm(p => ({ ...p, targetId: e.target.value }))}
                      style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    >
                      {intervalAlarm.targetType === 'client' 
                        ? clients.map(c => <option key={c.client_id} value={c.client_id}>{c.friendly_name}</option>)
                        : subgroups.map(g => <option key={g.group_id} value={g.group_id}>{g.name}</option>)
                      }
                      {((intervalAlarm.targetType === 'client' ? clients.length : subgroups.length) === 0) && <option value="">-- No Targets Available --</option>}
                    </select>
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Sequence Span (Sec)</label>
                      <input 
                        type="number" 
                        value={intervalAlarm.duration_sec}
                        onChange={e => setIntervalAlarm(p => ({ ...p, duration_sec: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Alarm Count</label>
                      <input 
                        type="number" 
                        value={intervalAlarm.count}
                        onChange={e => setIntervalAlarm(p => ({ ...p, count: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Action Duration</label>
                      <input 
                        type="number" 
                        step="0.1"
                        value={intervalAlarm.action_duration}
                        onChange={e => setIntervalAlarm(p => ({ ...p, action_duration: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Action</label>
                      <select 
                        value={intervalAlarm.action}
                        onChange={e => setIntervalAlarm(p => ({ ...p, action: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      >
                        <option value="play_sound">Play Sound</option>
                        <option value="record_audio">Record Audio</option>
                      </select>
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary mt-2">Generate Interval Sequence</button>
                </div>
              </form>
            )}

            {activeTab === 'tuning' && (
              <form onSubmit={handleAdjustInterval}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label className="text-secondary text-sm block mb-1">Sequence Parent ID</label>
                    <select
                      value={tuning.parent_id}
                      onChange={e => setTuning(p => ({ ...p, parent_id: e.target.value }))}
                      disabled={activeParentIds.length === 0}
                      style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                    >
                      {activeParentIds.length === 0 ? (
                        <option value="">No active intervals</option>
                      ) : (
                        activeParentIds.map(pid => {
                          const pending = alarms.filter(a => a.parent_id === pid && !a.fired).length;
                          return (
                            <option key={pid} value={pid}>
                              {pid} ({pending} pending)
                            </option>
                          );
                        })
                      )}
                    </select>
                  </div>

                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">New Spacing (Seconds)</label>
                      <input 
                        type="number" 
                        step="0.1"
                        value={tuning.spacing_sec}
                        onChange={e => setTuning(p => ({ ...p, spacing_sec: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label className="text-secondary text-sm block mb-1">Jitter (Milliseconds)</label>
                      <input 
                        type="number" 
                        value={tuning.jitter_ms}
                        onChange={e => setTuning(p => ({ ...p, jitter_ms: e.target.value }))}
                        style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '4px' }}
                      />
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary mt-2" disabled={!tuning.parent_id}>Adjust Interval Precision</button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Section: Active Alarm Table & Bulk Actions */}
      <div className="glass-panel mt-6">
        <div className="flex-between mb-4">
          <div>
            <h3>Active Alarms Schedule</h3>
            <p className="text-secondary text-sm">Review, enable, disable, and adjust pending alarms.</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn" onClick={() => handleBulkEdit(true)} disabled={selectedAlarms.length === 0}>Enable Selected</button>
            <button className="btn" onClick={() => handleBulkEdit(false)} disabled={selectedAlarms.length === 0}>Disable Selected</button>
            <button className="btn" onClick={() => handleToggleAll(true)}>Enable All</button>
            <button className="btn" onClick={() => handleToggleAll(false)}>Disable All</button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)' }}>
                <th style={{ padding: '12px' }}>
                  <input 
                    type="checkbox" 
                    onChange={toggleSelectAllAlarms}
                    checked={alarms.filter(a => !a.fired).length > 0 && selectedAlarms.length === alarms.filter(a => !a.fired).length}
                  />
                </th>
                <th style={{ padding: '12px' }}>Alarm ID</th>
                <th style={{ padding: '12px' }}>Target Clients</th>
                <th style={{ padding: '12px' }}>Trigger In</th>
                <th style={{ padding: '12px' }}>Action</th>
                <th style={{ padding: '12px' }}>Duration</th>
                <th style={{ padding: '12px' }}>Parent ID</th>
                <th style={{ padding: '12px' }}>State</th>
              </tr>
            </thead>
            <tbody>
              {alarms.map(a => {
                const remaining = Math.max(0, Math.ceil((a.trigger_time - Date.now()) / 1000));
                const isSelected = selectedAlarms.includes(a.alarm_id);
                return (
                  <tr key={a.alarm_id} style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    background: a.fired ? 'rgba(0,0,0,0.05)' : isSelected ? 'rgba(129,140,248,0.08)' : 'transparent',
                    opacity: a.fired ? 0.6 : 1
                  }}>
                    <td style={{ padding: '12px' }}>
                      <input 
                        type="checkbox" 
                        disabled={a.fired}
                        checked={isSelected}
                        onChange={() => toggleSelectAlarm(a.alarm_id)}
                      />
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 'bold' }}>{a.alarm_id}</td>
                    <td style={{ padding: '12px' }}>{getClientNames(a.client_ids)}</td>
                    <td style={{ padding: '12px' }}>
                      {a.fired ? 'FIRED' : `${remaining}s (${new Date(a.trigger_time).toLocaleTimeString()})`}
                    </td>
                    <td style={{ padding: '12px', textTransform: 'uppercase', fontSize: '12px' }}>{a.action}</td>
                    <td style={{ padding: '12px' }}>{a.duration.toFixed(1)}s</td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', color: '#a5b4fc' }}>{a.parent_id || 'None'}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ 
                        padding: '2px 8px', 
                        borderRadius: '10px', 
                        fontSize: '11px',
                        background: a.fired 
                          ? 'rgba(156,163,175,0.1)' 
                          : a.enabled 
                            ? 'rgba(16,185,129,0.2)' 
                            : 'rgba(239,68,68,0.2)',
                        color: a.fired 
                          ? '#9ca3af' 
                          : a.enabled 
                            ? '#34d399' 
                            : '#f87171'
                      }}>
                        {a.fired ? 'Fired' : a.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {alarms.length === 0 && (
                <tr>
                  <td colSpan="8" style={{ padding: '24px', textAlign: 'center', color: '#9ca3af', fontStyle: 'italic' }}>
                    No scheduled alarms. Create one above to begin!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Circadia;
