import React from 'react';
import {
  PREFLIGHT_STEPS,
  INRIDE_EDIT_RULES,
  OFFLINE_GUARANTEES,
} from '../../data/routeSession';

const STATUS_ICON = {
  ready: '✓',
  snapshotted: '✓',
  pending: '…',
  running: '◎',
};

const PreflightPanel = ({ stepStatus, onRunPreflight, isRunning, phase }) => {
  const allReady = Object.values(stepStatus).every((s) => s === 'ready' || s === 'snapshotted');

  return (
    <div className="preflight-panel">
      <h3>{phase === 'preflight' ? 'Preflight Processing' : 'In-Ride Edit Model'}</h3>

      {phase === 'preflight' && (
        <>
          <p className="text-sm text-secondary mt-2 mb-4">
            Nav benefits most from preflight — compute once, ride offline.
          </p>

          <ul className="preflight-checklist">
            {PREFLIGHT_STEPS.map((step) => (
              <li key={step.id} className="preflight-step">
                <span className={`step-status step-${stepStatus[step.id]}`}>
                  {STATUS_ICON[stepStatus[step.id]] || '·'}
                </span>
                <span className="text-sm">{step.label}</span>
                {step.requiresNetwork && (
                  <span className="step-net text-sm text-secondary">net once</span>
                )}
              </li>
            ))}
          </ul>

          <button
            type="button"
            className="btn btn-primary mt-4"
            onClick={onRunPreflight}
            disabled={isRunning || allReady}
          >
            {isRunning ? 'Processing…' : allReady ? 'Bundle ready' : 'Run preflight'}
          </button>
        </>
      )}

      {phase === 'inride' && (
        <>
          <p className="text-sm text-secondary mt-2 mb-4">
            Edit on the fly without weird reroutes — patches stay inside the preflight corridor.
          </p>

          <div className="edit-rules-grid mt-4">
            <div>
              <span className="text-sm text-accent">Can edit</span>
              <ul className="rule-list mt-2">
                {INRIDE_EDIT_RULES.allowed.map((r) => (
                  <li key={r} className="text-sm">{r}</li>
                ))}
              </ul>
            </div>
            <div>
              <span className="text-sm text-danger">Won't trigger</span>
              <ul className="rule-list mt-2">
                {INRIDE_EDIT_RULES.blocked.map((r) => (
                  <li key={r} className="text-sm text-secondary">{r}</li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}

      <div className="offline-guarantees mt-4">
        <span className="text-sm text-secondary">Offline guarantees</span>
        <ul className="rule-list mt-2">
          {OFFLINE_GUARANTEES.map((g) => (
            <li key={g} className="text-sm">{g}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default PreflightPanel;