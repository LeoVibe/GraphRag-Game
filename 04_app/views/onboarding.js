import { loadProfile, saveProfile, markOnboardingSeen } from '../storage.js';

const STEPS = [
  { title: '歡迎來到三國世界', body: '看看 60 位英雄各自做了什麼，你會慢慢認識他們。', icon: '🏞' },
  { title: '點亮的關卡可以挑戰', body: '從第一關開始，答對題目就能解鎖後面的故事。', icon: '🗺' },
  { title: '答對會學到人物的故事', body: '每答對一題，就會多認識一位英雄，圖鑑會慢慢填滿。', icon: '✨' },
];

export function showOnboarding(onDone) {
  let step = 0;
  const overlay = document.createElement('div');
  overlay.className = 'onboarding-overlay';
  document.body.appendChild(overlay);

  function render() {
    const s = STEPS[step];
    overlay.innerHTML = '<div class="onboarding-panel"><div class="onboarding-icon">' + s.icon + '</div><h2>' + s.title + '</h2><p>' + s.body + '</p><div class="onboarding-actions"><button class="btn" id="skipBtn">跳過</button><button class="btn is-primary" id="nextBtn">' + (step === STEPS.length - 1 ? '開始 →' : '下一步') + '</button></div><div class="onboarding-dots">' + STEPS.map((_, i) => '<span class="' + (i === step ? 'is-active' : '') + '"></span>').join('') + '</div></div>';
    overlay.querySelector('#skipBtn').addEventListener('click', finish);
    overlay.querySelector('#nextBtn').addEventListener('click', () => {
      if (step < STEPS.length - 1) {
        step++;
        render();
      } else {
        finish();
      }
    });
  }

  function finish() {
    overlay.remove();
    const profile = loadProfile();
    saveProfile(markOnboardingSeen(profile));
    if (onDone) onDone();
  }

  render();
}
