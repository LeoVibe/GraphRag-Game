import { loadProfile } from '../storage.js';

export function updateProgress(profile = null) {
  const p = profile || loadProfile();
  const known = Object.values(p.characters).filter(c => c.level >= 1).length;
  const fill = document.getElementById('progressFill');
  const text = document.getElementById('progressText');
  const target = 60;
  if (fill) fill.style.width = `${Math.min(100, (known / target) * 100)}%`;
  if (text) text.textContent = `${known} / ${target} ★${p.totalStars}`;
}
