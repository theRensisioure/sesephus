import React, { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import OptimizationStack from './OptimizationStack';
import BasinEditor from './BasinEditor';
import ParetoTray from './ParetoTray';
import RouteMap from './RouteMap';
import RiderProfileSelector from './RiderProfileSelector';
import VoiceSpeakerPanel from './VoiceSpeakerPanel';
import SessionPhaseBar from './SessionPhaseBar';
import PreflightPanel from './PreflightPanel';
import { RIDER_PROFILES, SATURNNAV_MISSION } from '../../data/riderProfiles';
import {
  MOCK_PREFLIGHT_STATUS,
  applyInRideWeightNudge,
} from '../../data/routeSession';
import { MOCK_ROUTES, MOCK_ORIGIN, MOCK_DEST, MOCK_BASINS } from '../../data/mockRoutes';

let basinCounter = 0;

const defaultProfile = RIDER_PROFILES.find((p) => p.id === 'unicycle');

const SaturnNavLab = () => {
  const [activeProfileId, setActiveProfileId] = useState('unicycle');
  const [weights, setWeights] = useState(
    Object.fromEntries(
      Object.entries(defaultProfile.defaultWeights).map(([k, v]) => [k, v * 100])
    )
  );
  const [activePreset, setActivePreset] = useState('Unicycle');
  const [activeRouteId, setActiveRouteId] = useState(MOCK_ROUTES[0].id);
  const [basins, setBasins] = useState(MOCK_BASINS);
  const [placingMode, setPlacingMode] = useState(false);
  const [sessionPhase, setSessionPhase] = useState('preflight');
  const [preflightStatus, setPreflightStatus] = useState(MOCK_PREFLIGHT_STATUS);
  const [bundleReady, setBundleReady] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [preflightRunning, setPreflightRunning] = useState(false);
  const [routePatchNote, setRoutePatchNote] = useState(null);

  const activeRoute = useMemo(
    () => MOCK_ROUTES.find((r) => r.id === activeRouteId) || MOCK_ROUTES[0],
    [activeRouteId]
  );

  const handleMapClick = useCallback(({ lat, lng }) => {
    basinCounter += 1;
    setBasins((prev) => [
      ...prev,
      {
        id: `basin-${basinCounter}`,
        center: { lat, lng },
        radius_m: 600,
        polarity: 'repel',
        strength: 0.7,
      },
    ]);
    setPlacingMode(false);
  }, []);

  const handleRemoveBasin = useCallback((id) => {
    setBasins((prev) => prev.filter((b) => b.id !== id));
  }, []);

  const handleTogglePolarity = useCallback((id) => {
    setBasins((prev) =>
      prev.map((b) =>
        b.id === id
          ? { ...b, polarity: b.polarity === 'attract' ? 'repel' : 'attract' }
          : b
      )
    );
  }, []);

  const handleProfileSelect = useCallback((profileId) => {
    const profile = RIDER_PROFILES.find((p) => p.id === profileId);
    if (!profile) return;
    setActiveProfileId(profileId);
    setWeights(
      Object.fromEntries(
        Object.entries(profile.defaultWeights).map(([k, v]) => [k, v * 100])
      )
    );
    setActivePreset(profile.name);
  }, []);

  const handleWeightsChange = useCallback((nextWeights) => {
    setWeights(nextWeights);
    if (sessionPhase === 'inride' && bundleReady) {
      const picked = applyInRideWeightNudge(MOCK_ROUTES, nextWeights);
      setActiveRouteId(picked);
      setRoutePatchNote('Switched to cached alternate — route held, no recalc.');
    }
  }, [sessionPhase, bundleReady]);

  const handleRunPreflight = useCallback(() => {
    setPreflightRunning(true);
    setTimeout(() => {
      setPreflightStatus({
        graph: 'ready',
        dem: 'ready',
        wind: 'snapshotted',
        pareto: 'ready',
        speaker: 'ready',
        bundle: 'ready',
      });
      setBundleReady(true);
      setPreflightRunning(false);
      setRoutePatchNote(null);
    }, 1200);
  }, []);

  const handlePhaseChange = useCallback((phase) => {
    if (phase === 'inride') {
      setIsOffline(true);
      setRoutePatchNote('Offline mode — editing from preflight bundle.');
    } else {
      setIsOffline(false);
      setRoutePatchNote(null);
    }
    setSessionPhase(phase);
  }, []);

  const inRideLocked = sessionPhase === 'inride';

  return (
    <div className="saturnnav-lab animate-fade-in">
      <div className="lab-header flex-between mb-4">
        <div>
          <span className="text-sm text-secondary">Shipment</span>
          <h2>🎡 SaturnNav <span className="text-accent text-sm">v0.1.0</span></h2>
          <p className="saturnnav-mission mt-2">{SATURNNAV_MISSION}</p>
        </div>
        <div className="flex-center gap-3">
          <span className={`badge ${bundleReady ? 'badge-success' : 'badge-warning'}`}>
            {bundleReady ? 'bundle ready' : 'preflight needed'}
          </span>
          <Link to="/shipments/saturnnav/manifest" className="btn">Manifest</Link>
          <Link to="/" className="btn">← Dock</Link>
        </div>
      </div>

      <SessionPhaseBar
        phase={sessionPhase}
        onPhaseChange={handlePhaseChange}
        isOffline={isOffline}
        bundleReady={bundleReady}
      />

      {routePatchNote && (
        <p className="route-patch-note text-sm mb-4">{routePatchNote}</p>
      )}

      <div className="lab-layout">
        <aside className="lab-sidebar glass-panel">
          <PreflightPanel
            phase={sessionPhase}
            stepStatus={preflightStatus}
            onRunPreflight={handleRunPreflight}
            isRunning={preflightRunning}
          />
          <RiderProfileSelector
            activeProfileId={activeProfileId}
            onSelect={handleProfileSelect}
          />
          <OptimizationStack
            weights={weights}
            onChange={handleWeightsChange}
            activePreset={activePreset}
            onPresetChange={setActivePreset}
          />
          <BasinEditor
            basins={basins}
            placingMode={placingMode && !inRideLocked}
            onStartPlace={() => !inRideLocked && setPlacingMode((p) => !p)}
            onAdd={() => !inRideLocked && setPlacingMode(true)}
            onRemove={handleRemoveBasin}
            onTogglePolarity={handleTogglePolarity}
          />
          {inRideLocked && (
            <p className="text-sm text-secondary mt-2">Basin add/remove locked in-ride — polarity flip ok.</p>
          )}
          <VoiceSpeakerPanel activeProfileName={RIDER_PROFILES.find((p) => p.id === activeProfileId)?.name} />
        </aside>

        <div className="lab-map-area glass-panel">
          <RouteMap
            routes={MOCK_ROUTES}
            activeRouteId={activeRouteId}
            origin={MOCK_ORIGIN}
            destination={MOCK_DEST}
            basins={basins}
            placingMode={placingMode}
            onMapClick={handleMapClick}
          />
        </div>
      </div>

      <div className="lab-tray glass-panel mt-4">
        <ParetoTray
          routes={MOCK_ROUTES}
          activeRouteId={activeRouteId}
          onSelect={setActiveRouteId}
          activeRoute={activeRoute}
        />
      </div>
    </div>
  );
};

export default SaturnNavLab;