const KEY = 'sanguo-codex-v1';

const DEFAULT = {
  unlockedPacks: ['ch001_010'],  // 第一包預設解鎖
  characters: {},                // { [nodeId]: { level: 1, correctAnswers: 0, wrongAnswers: 0, discoveredEdges: [] } }
  totalStars: 0,
  recentQuestions: [],           // [questionFingerprint] 最近 20 題防重出
  onboardingSeen: false,
  wrongStreak: 0,
  hintsUsed: 0,
  fontScale: 'normal',
};

export function loadProfile() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT, ...parsed };
  } catch {
    return { ...DEFAULT };
  }
}

export function saveProfile(profile) {
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch (e) {
    console.warn('saveProfile failed', e);
  }
}

export function markOnboardingSeen(profile) {
  return { ...profile, onboardingSeen: true };
}

export function setFontScale(profile, scale) {
  return { ...profile, fontScale: scale };
}

export function applyAnswerOutcome(profile, correct) {
  if (correct) return { ...profile, wrongStreak: 0 };
  return { ...profile, wrongStreak: profile.wrongStreak + 1 };
}

export function recordAnswer(profile, { nodeId, correct, questionFingerprint, edge }) {
  const next = { ...profile };
  next.characters = { ...next.characters };
  const cur = next.characters[nodeId] || { level: 0, correctAnswers: 0, wrongAnswers: 0, discoveredEdges: [] };
  const updated = { ...cur };
  if (correct) {
    updated.correctAnswers += 1;
    if (edge && !updated.discoveredEdges.includes(edge.id)) {
      updated.discoveredEdges = [...updated.discoveredEdges, edge.id];
    }
    // 升等規則：每 3 次正確 + ≥ 2 種題型 → +1 級（簡化：每 3 次正確 +1）
    const expectedLevel = Math.min(3, Math.floor(updated.correctAnswers / 3) + 1);
    if (expectedLevel > updated.level) {
      updated.level = expectedLevel;
      next.totalStars = next.totalStars + 1;
    }
  } else {
    updated.wrongAnswers += 1;
  }
  next.characters[nodeId] = updated;
  next.recentQuestions = [questionFingerprint, ...next.recentQuestions].slice(0, 20);
  return next;
}

export function unlockPack(profile, packId) {
  if (profile.unlockedPacks.includes(packId)) return profile;
  return { ...profile, unlockedPacks: [...profile.unlockedPacks, packId] };
}
