import React, { useCallback, useEffect, useState } from 'react';

const fmtBytes = (n) => {
  if (n == null || Number.isNaN(n)) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const Sieve = () => {
  const [root, setRoot] = useState('');
  const [defaults, setDefaults] = useState(null);
  const [scan, setScan] = useState(null);
  const [shredResult, setShredResult] = useState(null);
  const [unit, setUnit] = useState('conversation');
  const [force, setForce] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [busy, setBusy] = useState(null); // 'scan' | 'shred' | null
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/sieve/defaults');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (cancelled) return;
        setDefaults(json);
        if (json.artifact_roots?.length && !root) {
          setRoot(json.artifact_roots[0]);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            `Defaults unavailable (${err.message}). Is dashboard_server on :3001?`
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // keepShredResult: the post-shred refresh must not wipe the summary it is
  // refreshing for.
  const runScan = useCallback(async ({ keepShredResult = false } = {}) => {
    if (!root.trim()) {
      setError('Open a directory: paste the path to your Gemini/Takeout dump.');
      return;
    }
    setBusy('scan');
    setError(null);
    if (!keepShredResult) setShredResult(null);
    setSelected(null);
    try {
      const res = await fetch('/api/sieve/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ root: root.trim(), shallow: false }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} — is dashboard_server running on :3001?`);
      const json = await res.json();
      if (!json.ok) {
        setError(json.error || 'Scan failed');
        setScan(null);
        return;
      }
      setScan(json);
    } catch (err) {
      setError(`Scan failed: ${err.message}`);
      setScan(null);
    } finally {
      // Only clear if this flow still owns the slot.
      setBusy((b) => (b === 'scan' ? null : b));
    }
  }, [root]);

  const runShred = useCallback(async () => {
    if (!root.trim()) {
      setError('Open a directory first.');
      return;
    }
    setBusy('shred');
    setError(null);
    setShredResult(null);
    try {
      const res = await fetch('/api/sieve/shred', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          root: root.trim(),
          unit,
          force,
          dry_run: dryRun,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} — is dashboard_server running on :3001?`);
      const json = await res.json();
      if (!json.ok) {
        setError(json.error || 'Shred failed');
        setShredResult(null);
        return;
      }
      setShredResult(json);
      // Refresh inventory after shred so sievable/state stays honest
      await runScan({ keepShredResult: true });
    } catch (err) {
      setError(`Shred failed: ${err.message}`);
      setShredResult(null);
    } finally {
      setBusy((b) => (b === 'shred' ? null : b));
    }
  }, [root, unit, force, dryRun, runScan]);

  const files = scan?.files || [];

  return (
    <div className="sieve-module animate-fade-in">
      <h2>Artifact Sieve</h2>
      <p className="text-secondary" style={{ marginBottom: 16, maxWidth: 720 }}>
        Comb Google Gemini / Takeout chat dumps through the shredder. Open the
        directory Google gave you (unzipped Takeout, or a folder of
        <code style={{ margin: '0 4px' }}>conversations.json</code>
        files), scan the inventory, then shred into
        <code style={{ margin: '0 4px' }}>ingest/debris_shards.jsonl</code>
        for Forge.
      </p>

      <div className="glass-panel mt-6">
        <h3>Opened directory</h3>
        <p className="text-secondary mt-2" style={{ fontSize: '0.9rem' }}>
          {defaults?.hint ||
            'Point at …/Takeout/Gemini or the export folder from takeout.google.com.'}
        </p>
        <div
          className="mt-4"
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 12,
            alignItems: 'center',
          }}
        >
          <input
            type="text"
            value={root}
            onChange={(e) => setRoot(e.target.value)}
            placeholder="V:\exports\Takeout\Gemini  or  C:\Users\…\Downloads\takeout-…"
            spellCheck={false}
            style={{
              flex: '1 1 320px',
              minWidth: 240,
              background: 'rgba(0,0,0,0.35)',
              border: '1px solid var(--panel-border)',
              borderRadius: 10,
              color: 'var(--text-primary)',
              padding: '12px 14px',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.85rem',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !busy) runScan();
            }}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => runScan()}
            disabled={!!busy}
          >
            {busy === 'scan' ? 'Scanning…' : 'Scan directory'}
          </button>
        </div>

        {defaults?.artifact_roots?.length > 0 && (
          <div className="mt-4" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <span className="text-secondary text-sm">Quick roots:</span>
            {defaults.artifact_roots.map((r) => (
              <button
                key={r}
                type="button"
                className="btn btn-sm"
                onClick={() => setRoot(r)}
                title={r}
              >
                {r.length > 48 ? `…${r.slice(-44)}` : r}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div
          className="glass-panel mt-4"
          style={{ borderColor: 'var(--danger-color)' }}
        >
          <p style={{ color: 'var(--danger-color)', margin: 0 }}>{error}</p>
        </div>
      )}

      {scan && (
        <div className="glass-panel mt-6">
          <div className="flex-between" style={{ alignItems: 'flex-start' }}>
            <div>
              <h3 style={{ marginBottom: 8 }}>Artifact scanner</h3>
              <p className="text-secondary text-sm" style={{ margin: 0 }}>
                Root: <code>{scan.root || root}</code>
              </p>
            </div>
            <div className="text-secondary text-sm" style={{ textAlign: 'right' }}>
              <div>
                <strong style={{ color: 'var(--accent-color)' }}>{scan.file_count}</strong> files
              </div>
              <div>
                <strong style={{ color: 'var(--accent-color)' }}>
                  {scan.conversation_count}
                </strong>{' '}
                conversations
              </div>
              <div>
                <strong style={{ color: 'var(--accent-color)' }}>{scan.message_count}</strong>{' '}
                messages
              </div>
            </div>
          </div>

          <div
            className="mt-6"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 12,
              alignItems: 'center',
            }}
          >
            <label className="text-secondary text-sm" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              Unit
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                style={{
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid var(--panel-border)',
                  color: 'var(--text-primary)',
                  borderRadius: 8,
                  padding: '8px 10px',
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                <option value="conversation">conversation (1 chunk / chat)</option>
                <option value="turn">turn (1 chunk / message)</option>
              </select>
            </label>
            <label className="text-secondary text-sm" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
              />
              force re-shred
            </label>
            <label className="text-secondary text-sm" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              dry-run
            </label>
            <button
              type="button"
              className="btn btn-primary"
              onClick={runShred}
              disabled={!!busy || files.length === 0}
            >
              {busy === 'shred' ? 'Shredding…' : 'Shred through sieve'}
            </button>
          </div>

          {shredResult && (
            <>
              <p className="mt-4 text-sm" style={{ color: 'var(--success-color)' }}>
                {shredResult.dry_run ? (
                  <>
                    Dry run: would ship {shredResult.would_ship ?? 0} chunk(s) from{' '}
                    {shredResult.would_shred ?? 0} of {shredResult.files_seen ?? 0} file(s)
                    — nothing written
                  </>
                ) : (
                  <>
                    Shipped {shredResult.chunks_shipped} chunk(s) from{' '}
                    {shredResult.files_shredded} of {shredResult.files_seen ?? 0} file(s)
                    {shredResult.output ? ` → ${shredResult.output}` : ''}
                    {shredResult.chunks_shipped > 0 ? ' — next: python utils/forge.py' : ''}
                  </>
                )}
              </p>
              {shredResult.errors?.length > 0 && (
                <details className="mt-2 text-sm" style={{ color: 'var(--danger-color)' }}>
                  <summary style={{ cursor: 'pointer' }}>
                    {shredResult.errors.length} file(s) failed
                  </summary>
                  <ul style={{ paddingLeft: 18, marginTop: 8 }}>
                    {shredResult.errors.map((e, i) => (
                      <li key={`${e.path}:${i}`} style={{ marginBottom: 4 }}>
                        <code>{e.path}</code> — {e.error}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}

          {scan.root_problems?.length > 0 && (
            <div className="mt-4 text-sm" style={{ color: 'var(--danger-color)' }}>
              <p style={{ margin: 0 }}>
                {scan.root_problems.length} path(s) could not be read — this scan is incomplete:
              </p>
              <ul style={{ paddingLeft: 18, marginTop: 8 }}>
                {scan.root_problems.map((p, i) => (
                  <li key={`${p.path}:${i}`} style={{ marginBottom: 4 }}>
                    <code>{p.path}</code> — {p.error}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {files.length === 0 ? (
            <p className="text-secondary mt-6">
              No chat-export artifacts detected in this directory. Expected
              names like conversations.json, MyActivity.json, Gemini HTML, or
              files under a Takeout/Gemini tree.
            </p>
          ) : (
            <div
              className="mt-6"
              style={{
                overflowX: 'auto',
                maxHeight: 420,
                overflowY: 'auto',
                border: '1px solid var(--panel-border)',
                borderRadius: 12,
              }}
            >
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.78rem',
                }}
              >
                <thead>
                  <tr style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '10px 12px' }}>Name</th>
                    <th style={{ padding: '10px 12px' }}>Format</th>
                    <th style={{ padding: '10px 12px' }}>Size</th>
                    <th style={{ padding: '10px 12px' }}>Chats</th>
                    <th style={{ padding: '10px 12px' }}>Msgs</th>
                    <th style={{ padding: '10px 12px' }}>Sievable</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((f) => {
                    const active = selected?.path === f.path;
                    return (
                      <tr
                        key={f.path}
                        onClick={() => setSelected(f)}
                        style={{
                          cursor: 'pointer',
                          background: active
                            ? 'rgba(124, 247, 255, 0.08)'
                            : 'transparent',
                          borderTop: '1px solid var(--panel-border)',
                        }}
                      >
                        <td style={{ padding: '10px 12px' }} title={f.path}>
                          {f.name}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--accent-color)' }}>
                          {f.format}
                        </td>
                        <td style={{ padding: '10px 12px' }}>{fmtBytes(f.size_bytes)}</td>
                        <td style={{ padding: '10px 12px' }}>{f.conversation_count}</td>
                        <td style={{ padding: '10px 12px' }}>{f.message_count}</td>
                        <td style={{ padding: '10px 12px' }}>
                          {f.sievable === true && (
                            <span style={{ color: 'var(--success-color)' }}>yes</span>
                          )}
                          {f.sievable === false && (
                            <span style={{ color: 'var(--text-secondary)' }}>no</span>
                          )}
                          {f.sievable == null && (
                            <span
                              style={{ color: 'var(--text-secondary)' }}
                              title={f.deep_parse_skipped || f.error || 'not deep-parsed'}
                            >
                              ?
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {selected && (
            <div className="glass-panel-sm mt-4" style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: '0.95rem' }}>Selected artifact</h3>
              <p className="text-secondary text-sm" style={{ wordBreak: 'break-all' }}>
                {selected.path}
              </p>
              {selected.sample_titles?.length > 0 && (
                <div className="mt-4">
                  <p className="text-secondary text-sm" style={{ marginBottom: 8 }}>
                    Sample titles
                  </p>
                  <ul style={{ paddingLeft: 18, margin: 0 }}>
                    {selected.sample_titles.map((t, i) => (
                      <li key={`${selected.path}:${i}`} style={{ marginBottom: 4 }}>
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {selected.deep_parse_skipped && (
                <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
                  {selected.deep_parse_skipped}
                </p>
              )}
              {selected.error && (
                <p style={{ color: 'var(--danger-color)', marginTop: 8 }}>
                  {selected.error}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="glass-panel mt-6">
        <h3>CLI (same pipeline)</h3>
        <pre
          className="text-secondary"
          style={{
            marginTop: 12,
            whiteSpace: 'pre-wrap',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.8rem',
            lineHeight: 1.5,
          }}
        >{`# Inventory only
python shredder/artifact_sieve.py --scan-only --root "PATH\\TO\\Takeout\\Gemini"

# Shred → ingest/debris_shards.jsonl
python shredder/artifact_sieve.py --root "PATH\\TO\\Takeout\\Gemini"

# Then vectorize
python utils/forge.py`}</pre>
      </div>
    </div>
  );
};

export default Sieve;
