const SEEN_KEY = 'sanguo-v18-onboarding-seen';

const STEPS = [
  {
    icon: '🗺',
    title: '三種探險方式',
    body: '人物探險 / 戰役推理 / 關係路徑 — 點上方三個分頁切換，每種會自動換色換景。',
  },
  {
    icon: '🔗',
    title: '會自己動的關係圖',
    body: '中央地圖用力導圖譜畫關係。可以點任一個人物換成主角，也可以拖動節點換位置。',
  },
  {
    icon: '⚙',
    title: '更多設定在這裡',
    body: '右上 ⚙ 設定可以調章節範圍、字級大小，也可以跳去玩「人物圖鑑挑戰」答題遊戲。',
  },
];

export function hasSeenOnboarding() {
  try { return localStorage.getItem(SEEN_KEY) === '1'; }
  catch { return false; }
}

export function markOnboardingSeen() {
  try { localStorage.setItem(SEEN_KEY, '1'); }
  catch {}
}

export function showOnboarding(onDone) {
  let step = 0;
  const overlay = document.createElement('div');
  overlay.className = 'onboarding-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  document.body.appendChild(overlay);

  function close() {
    overlay.remove();
    markOnboardingSeen();
    if (onDone) onDone();
  }

  function render() {
    const s = STEPS[step];
    const isLast = step === STEPS.length - 1;
    overlay.innerHTML = `
      <div class="onboarding-panel">
        <div class="onboarding-icon" aria-hidden="true">${s.icon}</div>
        <h2>${s.title}</h2>
        <p>${s.body}</p>
        <div class="onboarding-actions">
          <button type="button" class="onboarding-btn" data-action="skip">跳過</button>
          <button type="button" class="onboarding-btn is-primary" data-action="next">${isLast ? '開始探險 →' : '下一步'}</button>
        </div>
        <div class="onboarding-dots" aria-hidden="true">
          ${STEPS.map((_, i) => `<span class="${i === step ? 'is-active' : ''}"></span>`).join('')}
        </div>
      </div>
    `;
    overlay.querySelector('[data-action="skip"]').addEventListener('click', close);
    overlay.querySelector('[data-action="next"]').addEventListener('click', () => {
      if (isLast) return close();
      step += 1;
      render();
    });
  }

  function onKey(e) {
    if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onKey); }
  }
  document.addEventListener('keydown', onKey);

  render();
}
