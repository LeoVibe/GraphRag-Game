import { CHAPTER_PACKS, pickSubject, pickEdge, buildQuestion, chooseQuestionType, questionFingerprint } from '../engine.js';
import { getState, setState } from '../state.js';
import { loadProfile, saveProfile, recordAnswer, unlockPack } from '../storage.js';
import { goto } from '../router.js';
import { updateProgress } from './components.js';

export function renderStage(mainEl) {
  const state = getState();
  const pack = CHAPTER_PACKS.find(p => p.id === state.currentPackId);
  if (!pack) {
    mainEl.innerHTML = '<p>請先從地圖選擇關卡。</p>';
    return;
  }
  if (!state.currentQuestion) {
    const q = generateNewQuestion(state, pack);
    if (!q) {
      mainEl.innerHTML = '<p>本包出不出更多題了 — 已達 MVP 邊界。</p>';
      return;
    }
    setState({ currentQuestion: q, selectedChoice: null });
  }
  const q = getState().currentQuestion;
  mainEl.innerHTML = `
    <section class="stage" aria-label="當前任務">
      <header class="stage-header">
        <span class="meta">${pack.label} · 第 ${getState().questionsAnswered + 1} / ${getState().questionsTarget} 題</span>
      </header>
      <h2 class="stage-question">${q.prompt}</h2>
      ${q.clue ? `<div class="clue-card">線索：${q.clue}</div>` : ''}
      <div class="choices" role="radiogroup">
        ${q.choices.map(c => `
          <button class="choice" role="radio" aria-checked="false"
                  data-choice-id="${c.id}">${c.name}</button>
        `).join('')}
      </div>
      <div class="stage-actions">
        <button class="btn" id="skipBtn">換題目</button>
        <button class="btn is-primary" id="submitBtn" disabled>交卷</button>
      </div>
    </section>
  `;
  setupStageEvents(mainEl, q, pack);
}

function generateNewQuestion(state, pack) {
  const { data } = state;
  if (!data) return null;
  const { nodes, rels } = data;
  const byId = new Map(nodes.map(n => [n.id, n]));
  const profile = loadProfile();
  for (let attempt = 0; attempt < 20; attempt++) {
    const subject = pickSubject(nodes, pack, profile);
    if (!subject) continue;
    const subjectLevel = profile.characters[subject.id]?.level ?? 0;
    const type = chooseQuestionType(profile, subjectLevel);
    if (type === 'who-doesnt-belong') {
      const q = buildQuestion({ subject, edge: null, allNodes: nodes, type, byId });
      if (q) return q;
      continue;
    }
    const edge = pickEdge(subject, rels, pack, profile);
    if (!edge) continue;
    const q = buildQuestion({ subject, edge, allNodes: nodes, type, byId });
    if (!q) continue;
    if (profile.recentQuestions.includes(questionFingerprint(q))) continue;
    return q;
  }
  return null;
}

function setupStageEvents(mainEl, q, pack) {
  mainEl.querySelectorAll('.choice').forEach(btn => {
    btn.addEventListener('click', () => {
      mainEl.querySelectorAll('.choice').forEach(b => {
        b.classList.remove('is-selected');
        b.setAttribute('aria-checked', 'false');
      });
      btn.classList.add('is-selected');
      btn.setAttribute('aria-checked', 'true');
      setState({ selectedChoice: btn.dataset.choiceId });
      mainEl.querySelector('#submitBtn').disabled = false;
    });
  });
  mainEl.querySelector('#submitBtn').addEventListener('click', () => {
    submit(q, pack, mainEl);
  });
  mainEl.querySelector('#skipBtn').addEventListener('click', () => {
    setState({ currentQuestion: null, selectedChoice: null });
    renderStage(mainEl);
  });
}

function submit(q, pack, mainEl) {
  const chosen = getState().selectedChoice;
  const correct = chosen === q.correctChoiceId;
  const profile = loadProfile();
  const subject = q.subject;
  const explanation = q.edge?.description?.split('；')[0] || `${subject.name} 跟 ${q.choices.find(c => c.id === q.correctChoiceId)?.name} 在這場故事裡有關聯。`;
  const updated = recordAnswer(profile, {
    nodeId: subject.id,
    correct,
    questionFingerprint: questionFingerprint(q),
    edge: q.edge,
  });
  saveProfile(updated);
  showVerdict(mainEl, { correct, explanation, q, pack, updated });
}

function showVerdict(mainEl, { correct, explanation, q, pack, updated }) {
  const overlay = document.createElement('div');
  overlay.className = `overlay ${correct ? 'is-correct' : 'is-wrong'}`;
  overlay.innerHTML = `
    <div class="panel">
      <h2>${correct ? '✨ 答對了！' : '再想想看，差一點 🌱'}</h2>
      <p class="why">${explanation}</p>
      <div class="overlay-actions">
        <button class="btn" id="nextBtn">下一題</button>
        <button class="btn is-primary" id="backBtn">回地圖</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  updateProgress(updated);
  overlay.querySelector('#nextBtn').addEventListener('click', () => {
    overlay.remove();
    const nextAnswered = getState().questionsAnswered + 1;
    setState({ currentQuestion: null, selectedChoice: null, questionsAnswered: nextAnswered });
    if (nextAnswered >= getState().questionsTarget) {
      const nextPack = unlockNextPack(updated, pack);
      saveProfile(nextPack);
      alert('本關卡完成！下一包已解鎖。');
      goto('map');
    } else {
      renderStage(mainEl);
    }
  });
  overlay.querySelector('#backBtn').addEventListener('click', () => {
    overlay.remove();
    goto('map');
  });
}

function unlockNextPack(profile, pack) {
  const idx = CHAPTER_PACKS.findIndex(p => p.id === pack.id);
  if (idx === -1 || idx === CHAPTER_PACKS.length - 1) return profile;
  const next = CHAPTER_PACKS[idx + 1];
  return unlockPack(profile, next.id);
}
