import { CHAPTER_PACKS } from '../engine.js';
import { goto } from '../router.js';
import { getState, setState } from '../state.js';
import { loadProfile, unlockPack, saveProfile } from '../storage.js';

export function renderMap(mainEl) {
  const profile = loadProfile();
  mainEl.innerHTML = `
    <section class="map-grid" aria-label="事件包選擇">
      ${CHAPTER_PACKS.map(pack => mapNodeHtml(pack, profile)).join('')}
    </section>
  `;
  mainEl.querySelectorAll('.map-node').forEach(el => {
    el.addEventListener('click', () => {
      const packId = el.dataset.packId;
      const pack = CHAPTER_PACKS.find(p => p.id === packId);
      if (!profile.unlockedPacks.includes(packId)) {
        el.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-6px)' },
          { transform: 'translateX(6px)' }, { transform: 'translateX(0)' }], { duration: 250 });
        return;
      }
      setState({ currentPackId: packId, questionsAnswered: 0, currentQuestion: null });
      document.querySelector('[data-route="stage"]').disabled = false;
      goto('stage');
    });
  });
}

function mapNodeHtml(pack, profile) {
  const isUnlocked = profile.unlockedPacks.includes(pack.id);
  const completedCount = Object.entries(profile.characters)
    .filter(([, c]) => c.level >= 1).length;
  const lockIcon = isUnlocked ? '' : '🔒';
  const stars = isUnlocked ? '★★★☆☆' : '';
  return `
    <button class="card map-node ${isUnlocked ? '' : 'is-locked'}" data-pack-id="${pack.id}">
      <h3>${lockIcon} ${pack.label}</h3>
      <div class="meta">第 ${pack.start}-${pack.end} 回</div>
      <div class="meta">${pack.focus}</div>
      ${stars ? `<div class="stars">${stars}</div>` : ''}
    </button>
  `;
}
