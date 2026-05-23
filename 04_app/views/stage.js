import { CHAPTER_PACKS, pickSubject, pickEdge, buildQuestion, chooseQuestionType, questionFingerprint } from '../engine.js';
import { getState, setState } from '../state.js';
import { shouldShowHint, shouldForceAdvance } from '../safeguards.js';
import { loadProfile, saveProfile, recordAnswer, unlockPack, applyAnswerOutcome } from '../storage.js';
import { goto } from '../router.js';
import { updateProgress } from './components.js';
import { flashCardOnCorrect, toastNewCharacter, confettiBurst } from './celebrations.js';
import { makeDraggable, makeDropZone } from './dnd.js';

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
    setState({ currentQuestion: q, selectedChoice: null, matchAttempt: {} });
  }
  const currentState = getState();
  const q = currentState.currentQuestion;
  const submitDisabled = isSubmitDisabled(q, currentState);
  mainEl.innerHTML = `
    <section class="stage" aria-label="當前任務">
      <header class="stage-header">
        <span class="meta">${pack.label} · 第 ${currentState.questionsAnswered + 1} / ${currentState.questionsTarget} 題</span>
      </header>
      <h2 class="stage-question">${q.prompt}</h2>
      ${q.clue ? `<div class="clue-card">線索：${q.clue}</div>` : ''}
      ${renderQuestionBody(q, currentState)}
      <div class="stage-actions">
        <button class="btn" id="skipBtn">換題目</button>
        <button class="btn is-primary" id="submitBtn" ${submitDisabled ? 'disabled' : ''}>交卷</button>
      </div>
    </section>
  `;
  setupStageEvents(mainEl, q, pack);
}

function generateNewQuestion(state, pack) {
  const { data } = state;
  if (!data) return null;
  const { nodes, rels, personality } = data;
  const byId = new Map(nodes.map(n => [n.id, n]));
  const profile = loadProfile();
  for (let attempt = 0; attempt < 20; attempt++) {
    const subject = pickSubject(nodes, pack, profile);
    if (!subject) continue;
    const subjectLevel = profile.characters[subject.id]?.level ?? 0;
    const type = chooseQuestionType(profile, subjectLevel);
    if (type === 'personality-match') {
      const q = buildQuestion({
        subject: null, edge: null, allNodes: nodes, type, byId,
        rels, personality, pack, profile,
      });
      if (q && !profile.recentQuestions.includes(questionFingerprint(q))) return withHintMode(q, profile);
      continue;
    }
    if (type === 'who-doesnt-belong' || type === 'relation-chain') {
      const q = buildQuestion({
        subject, edge: null, allNodes: nodes, type, byId,
        rels, personality, pack, profile,
      });
      if (q) return withHintMode(q, profile);
      continue;
    }
    const edge = pickEdge(subject, rels, pack, profile);
    if (!edge) continue;
    const q = buildQuestion({
      subject, edge, allNodes: nodes, type, byId,
      rels, personality, pack, profile,
    });
    if (!q) continue;
    if (profile.recentQuestions.includes(questionFingerprint(q))) continue;
    return withHintMode(q, profile);
  }
  return null;
}

function withHintMode(q, profile) {
  return shouldShowHint(profile) ? { ...q, hintMode: true } : q;
}

function setupStageEvents(mainEl, q, pack) {
  if (q.type === 'personality-match') {
    setupPersonalityMatchEvents(mainEl, q);
  } else {
    setupChoiceEvents(mainEl);
  }
  mainEl.querySelector('#submitBtn').addEventListener('click', () => {
    submit(q, pack, mainEl);
  });
  mainEl.querySelector('#skipBtn').addEventListener('click', () => {
    setState({ currentQuestion: null, selectedChoice: null, matchAttempt: {} });
    renderStage(mainEl);
  });
}

function setupChoiceEvents(mainEl) {
  mainEl.querySelectorAll('.choice[data-choice-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      mainEl.querySelectorAll('.choice[data-choice-id]').forEach(b => {
        b.classList.remove('is-selected');
        b.setAttribute('aria-checked', 'false');
      });
      btn.classList.add('is-selected');
      btn.setAttribute('aria-checked', 'true');
      setState({ selectedChoice: btn.dataset.choiceId });
    });
  });
}

function setupPersonalityMatchEvents(mainEl, q) {
  mainEl.querySelectorAll('.trait-card[data-trait-label]').forEach(card => {
    makeDraggable(card, { traitLabel: card.dataset.traitLabel });
  });
  mainEl.querySelectorAll('.match-zone[data-character-id]').forEach(zone => {
    makeDropZone(zone, payload => {
      const traitLabel = payload?.traitLabel;
      if (!q.matchPairs.some(p => p.traitLabel === traitLabel)) return;
      setState({
        matchAttempt: {
          ...(getState().matchAttempt || {}),
          [traitLabel]: zone.dataset.characterId,
        },
      });
    });
  });
}

function submit(q, pack, mainEl) {
  const state = getState();
  const correct = q.type === 'personality-match'
    ? q.matchPairs.every(p => state.matchAttempt?.[p.traitLabel] === p.characterId)
    : state.selectedChoice === q.correctChoiceId;
  const profile = loadProfile();
  const subject = q.subject;
  const explanation = buildExplanation(q);
  const beforeLevel = profile.characters[subject?.id]?.level ?? 0;
  const updated = recordAnswer(profile, {
    nodeId: subject.id,
    correct,
    questionFingerprint: questionFingerprint(q),
    edge: q.edge,
  });
  const withOutcome = applyAnswerOutcome(updated, correct);
  saveProfile(withOutcome);
  const afterLevel = withOutcome.characters[subject?.id]?.level ?? 0;

  if (correct) {
    const choiceEl = mainEl.querySelector('.choice.is-selected');
    if (choiceEl) flashCardOnCorrect(choiceEl);
    if (afterLevel > beforeLevel) toastNewCharacter(subject.name);
    const knownNow = Object.values(withOutcome.characters).filter(c => c.level >= 1).length;
    const knownBefore = Object.values(profile.characters).filter(c => c.level >= 1).length;
    if (knownBefore < knownNow && knownNow % 10 === 0) confettiBurst();
  }

  if (!correct && shouldForceAdvance(withOutcome)) {
    showVerdict(mainEl, { correct: true, forced: true, explanation: '沒關係，這場我們先過去，回頭再來 🌱', q, pack, updated: withOutcome });
    return;
  }
  showVerdict(mainEl, { correct, explanation, q, pack, updated: withOutcome });
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
    setState({ currentQuestion: null, selectedChoice: null, matchAttempt: {}, questionsAnswered: nextAnswered });
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

function renderQuestionBody(q, state) {
  if (q.type === 'personality-match') {
    return renderPersonalityMatch(q, state.matchAttempt || {});
  }
  return `
    <div class="choices${q.type === 'relation-chain' ? ' relation-chain-choices' : ''}" role="radiogroup">
      ${q.choices.map(c => renderChoice(q, c, state.selectedChoice)).join('')}
    </div>
  `;
}

function renderChoice(q, choice, selectedChoice) {
  const selected = selectedChoice === choice.id;
  const body = q.type === 'relation-chain'
    ? `<span class="mini-path"><span>${q.subject.name}</span><span aria-hidden="true">→</span><strong>${choice.name}</strong><span aria-hidden="true">→</span><span>${q.endNode?.name || '目標'}</span></span>`
    : choice.name;
  return `
    <button class="choice${selected ? ' is-selected' : ''}" role="radio" aria-checked="${selected ? 'true' : 'false'}"
            data-choice-id="${choice.id}">${body}</button>
  `;
}

function renderPersonalityMatch(q, matchAttempt) {
  return `
    <div class="personality-match" aria-label="個性配對題">
      <div class="choices match-zones" aria-label="人物配對區">
        ${q.choices.map(c => renderMatchZone(c, matchAttempt)).join('')}
      </div>
      <div class="choices trait-cards" aria-label="個性敘述">
        ${q.choices.map(c => `
          <button class="choice trait-card${matchAttempt[c.traitLabel] ? ' is-selected' : ''}" type="button"
                  data-trait-label="${c.traitLabel}">${c.traitLabel}</button>
        `).join('')}
      </div>
    </div>
  `;
}

function renderMatchZone(choice, matchAttempt) {
  const assignedTraits = Object.entries(matchAttempt)
    .filter(([, characterId]) => characterId === choice.id)
    .map(([traitLabel]) => traitLabel);
  const assigned = assignedTraits.length ? assignedTraits.join('、') : '拖到這裡';
  return `
    <div class="choice match-zone" role="button" tabindex="0"
         data-character-id="${choice.id}" aria-label="把個性拖到 ${choice.name}">
      <span class="portrait" aria-hidden="true">${[...choice.name][0]}</span>
      <strong>${choice.name}</strong>
      <span class="assigned-trait">${assigned}</span>
    </div>
  `;
}

function isSubmitDisabled(q, state) {
  if (q.type === 'personality-match') {
    return !q.matchPairs.every(p => state.matchAttempt?.[p.traitLabel]);
  }
  return !state.selectedChoice;
}

function buildExplanation(q) {
  if (q.type === 'relation-chain') {
    return `${q.subject.name} 先經過 ${q.middleNode.name}，再連到 ${q.endNode.name}。`;
  }
  if (q.type === 'personality-match') {
    const nameById = new Map(q.choices.map(c => [c.id, c.name]));
    return `答案：${q.matchPairs.map(p => `${nameById.get(p.characterId)}是「${p.traitLabel}」`).join('；')}`;
  }
  return q.edge?.description?.split('；')[0]
    || `${q.subject.name} 跟 ${q.choices.find(c => c.id === q.correctChoiceId)?.name} 在這場故事裡有關聯。`;
}

function unlockNextPack(profile, pack) {
  const idx = CHAPTER_PACKS.findIndex(p => p.id === pack.id);
  if (idx === -1 || idx === CHAPTER_PACKS.length - 1) return profile;
  const next = CHAPTER_PACKS[idx + 1];
  return unlockPack(profile, next.id);
}
