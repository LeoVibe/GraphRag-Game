const HINT_PREFIX = 'sanguo-v18-hint-closed-';

const HINTS = {
  person: '點任一個人物換成他為主角；陣營一樣的會自動聚在一起。拖節點看會怎麼動。',
  battle: '點下方四步推理板（1 原因 → 2 決策 → 3 行動 → 4 結果）看戰役怎麼打的。',
  relation: '兩格選人後系統會找出最短路徑，看下方分段閱讀理解中間人怎麼串起來。',
};

export function hintChipHtml(mode) {
  try {
    if (localStorage.getItem(HINT_PREFIX + mode) === '1') return '';
  } catch {}
  const text = HINTS[mode] || '';
  if (!text) return '';
  return `
    <div class="map-hint" data-hint-mode="${mode}">
      <span class="map-hint-icon" aria-hidden="true">💡</span>
      <span class="map-hint-text">${text}</span>
      <button type="button" class="map-hint-close" aria-label="關閉提示">×</button>
    </div>
  `;
}

export function bindHintChip(container) {
  const hint = container.querySelector('.map-hint');
  if (!hint) return;
  hint.querySelector('.map-hint-close')?.addEventListener('click', () => {
    const mode = hint.dataset.hintMode;
    if (mode) {
      try { localStorage.setItem(HINT_PREFIX + mode, '1'); } catch {}
    }
    hint.classList.add('is-hidden');
  });
}
