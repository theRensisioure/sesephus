// SSFS path resolver — every vault path is derived from drive-mapping.json.
// Usage:
//   const { getVaultPath, getAudioJournalPath } = require('./paths');

'use strict';

const path = require('path');
const { loadMapping } = require('./config-engine');

function vaultRoot(mapping = loadMapping()) {
  return path.join(mapping.drives.vault.letter + '\\', mapping.paths.vaultRoot);
}

// getVaultPath('state') -> V:\ssfs-vault\state
function getVaultPath(sub = '', mapping = loadMapping()) {
  return sub ? path.join(vaultRoot(mapping), sub) : vaultRoot(mapping);
}

// getAudioJournalPath(new Date()) -> V:\ssfs-vault\audio\journal-2026-07-03_14-30-00.wav
// Accepts a Date, an epoch-ms number, or a pre-formatted string stamp.
function getAudioJournalPath(ts = new Date(), ext = '.wav', mapping = loadMapping()) {
  const stamp = typeof ts === 'string' ? ts : formatStamp(new Date(ts));
  return path.join(getVaultPath(mapping.paths.audio, mapping), `journal-${stamp}${ext}`);
}

// getMainVaultDbPath() -> V:\sesephus_vault.db (or from mapping.paths.vaultDb)
// This unifies the old main encrypted DB under the same drive discipline.
function getMainVaultDbPath(mapping = loadMapping()) {
  const letter = mapping.drives.vault.letter;
  const root = letter.endsWith('\\') ? letter : letter + '\\';
  const dbName = mapping.paths.vaultDb || 'sesephus_vault.db';
  return path.join(root, dbName);
}

function formatStamp(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}` +
         `_${p(d.getHours())}-${p(d.getMinutes())}-${p(d.getSeconds())}`;
}

module.exports = { vaultRoot, getVaultPath, getAudioJournalPath, getMainVaultDbPath, formatStamp };
