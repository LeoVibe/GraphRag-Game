function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function flashCardOnCorrect(targetEl) {
  if (!targetEl) return;
  if (reducedMotion()) {
    targetEl.style.opacity = '0.8';
    setTimeout(() => {
      targetEl.style.opacity = '';
    }, 80);
    return;
  }
  targetEl.classList.add('is-flash-correct');
  targetEl.addEventListener('animationend', () => targetEl.classList.remove('is-flash-correct'), { once: true });
}

export function toastNewCharacter(name) {
  const isReducedMotion = reducedMotion();
  const el = document.createElement('div');
  el.className = 'toast';
  if (isReducedMotion) el.style.animation = 'none';
  el.textContent = '新人物：' + name + ' 加入圖鑑！';
  document.body.appendChild(el);
  if (isReducedMotion) {
    setTimeout(() => el.remove(), 80);
    return;
  }
  setTimeout(() => {
    el.classList.add('is-out');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  }, 3000);
}

export function confettiBurst() {
  if (reducedMotion()) return;
  const container = document.createElement('div');
  container.className = 'confetti';
  const colors = ['#f87171', '#fb923c', '#fbbf24', '#34d399', '#60a5fa', '#a78bfa', '#f472b6'];
  for (let i = 0; i < 30; i++) {
    const span = document.createElement('span');
    span.style.left = Math.random() * 100 + 'vw';
    span.style.background = colors[Math.floor(Math.random() * colors.length)];
    span.style.animationDelay = Math.random() * 0.5 + 's';
    span.style.transform = 'rotate(' + Math.random() * 360 + 'deg)';
    container.appendChild(span);
  }
  document.body.appendChild(container);
  setTimeout(() => container.remove(), 2200);
}
