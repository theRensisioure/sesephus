export const RIDER_PROFILES = [
  {
    id: 'unicycle',
    name: 'Unicycle',
    icon: '🎡',
    featured: true,
    tagline: 'Especially unicyclers. Fewer words, longer gaps between them.',
    hints: ['steep bits only when needed', 'skips cobblestone unless close', 'one thing at a time'],
    defaultWeights: { altitude: 0.40, wind: 0.25, surface: 0.30, distance: 0.05 },
  },
  {
    id: 'acoustic',
    name: 'Acoustic',
    icon: '🚲',
    featured: false,
    tagline: 'Legs only. Hill mention if it matters — not every block.',
    hints: ['sparse grade notes', 'wind only when notable', 'no lane-by-lane chatter'],
    defaultWeights: { altitude: 0.35, wind: 0.30, surface: 0.20, distance: 0.15 },
  },
  {
    id: 'lithium_ion',
    name: 'Lithium Ion',
    icon: '⚡',
    featured: false,
    tagline: 'E-assist. Battery/climb note once, then silence.',
    hints: ['single climb heads-up', 'headwind if sustained', 'no repeated reminders'],
    defaultWeights: { altitude: 0.45, wind: 0.30, surface: 0.15, distance: 0.10 },
  },
  {
    id: 'gas',
    name: 'Gas',
    icon: '🔥',
    featured: false,
    tagline: 'Loud wheels. Traffic mention when it changes — not a running log.',
    hints: ['traffic only on change', 'range note at start', 'no stacked alerts'],
    defaultWeights: { altitude: 0.20, wind: 0.15, surface: 0.25, distance: 0.40 },
  },
];

export const SATURNNAV_TAGLINE =
  'Low-stimulus nav — the road is already a lot.';

export const SATURNNAV_MISSION =
  'Bikers, gas, lithium ion, acoustic, hell even unicyclers. Especially unicyclers. ' +
  'SaturnNav doesn\'t pile on: short phrases, long quiet stretches, limited understanding on purpose. ' +
  'Less nav noise so you can process what\'s actually in front of you.';

export const STIMULUS_LEVELS = [
  {
    id: 'whisper',
    label: 'Whisper',
    description: 'Junctions and real changes only. Minutes of silence between cues.',
    maxPhrasesPerKm: 1,
  },
  {
    id: 'sparse',
    label: 'Sparse',
    description: 'Occasional terrain or wind note. Never stacks two alerts.',
    maxPhrasesPerKm: 2,
  },
  {
    id: 'quiet',
    label: 'Quiet',
    description: 'Start-of-ride briefing, then mostly hands-off.',
    maxPhrasesPerKm: 0.5,
  },
];

export const VOICE_SAMPLE_LINES = [
  { trigger: 'upcoming grade', line: 'little uphill soon.' },
  { trigger: 'what it skips', line: '(no turn-by-turn every block. no recap of what you just passed.)' },
  { trigger: 'unicycle + rough surface', line: 'cobblestone up ahead — left side maybe.' },
  { trigger: 'why limited', line: 'narrow scope on purpose. road stimuli is enough.' },
];

export const STIMULUS_AVOIDS = [
  'rapid-fire turn instructions',
  'overlapping voice + visual alerts',
  'repeating the same cue',
  'asking questions mid-ride',
  'dense ETA / reroute chatter',
];