// 12 個事件包定義
export const CHAPTER_PACKS = [
  { id: 'ch001_010', label: '英雄起義', shortLabel: '1-10', start: 1, end: 10,
    focus: '桃園結義、黃巾之亂、董卓進京' },
  { id: 'ch011_020', label: '群雄角力', shortLabel: '11-20', start: 11, end: 20,
    focus: '曹操、呂布、袁術與劉備反覆交手' },
  { id: 'ch021_030', label: '官渡前後', shortLabel: '21-30', start: 21, end: 30,
    focus: '袁紹與曹操的勢力走向決戰' },
  { id: 'ch031_040', label: '荊州伏龍', shortLabel: '31-40', start: 31, end: 40,
    focus: '劉備尋找軍師，諸葛亮開始出場' },
  { id: 'ch041_050', label: '赤壁鏖兵', shortLabel: '41-50', start: 41, end: 50,
    focus: '孫劉合作，用火攻改變三國局勢' },
  { id: 'ch051_060', label: '荊南西川', shortLabel: '51-60', start: 51, end: 60,
    focus: '三方勢力各自延伸，準備走向三足鼎立' },
];

const QUESTION_TYPES = ['who-is-this', 'what-relation', 'who-doesnt-belong'];
// MVP 先實作三種，'relation-chain', 'personality-match' 留待 Phase 3

export function chooseQuestionType(profile, subjectLevel = 0) {
  // 簡化：依據人物熟識度選題型；MVP 跑 3 種
  if (subjectLevel === 0) return 'who-is-this';
  if (subjectLevel === 1) return 'what-relation';
  return 'who-doesnt-belong';
}

export function chapterOverlap(chapters, range) {
  if (!chapters || !chapters.length) return false;
  return chapters.some(c => c >= range.start && c <= range.end);
}

export function pickSubject(nodes, pack, profile) {
  const candidates = nodes.filter(n =>
    n.kind === 'entity' && n.type === 'character' && n.isTrunk
    && chapterOverlap(n.chapters, pack)
  );
  if (!candidates.length) return null;
  // 加權挑選：已 ★★★ 熟識 → 權重 0.2；未認識 → 權重 1.0
  const weighted = candidates.map(n => {
    const level = profile.characters[n.id]?.level ?? 0;
    const weight = level >= 3 ? 0.2 : (level === 0 ? 1.0 : 0.6);
    return { node: n, weight };
  });
  return weightedPick(weighted);
}

function weightedPick(items) {
  const total = items.reduce((s, x) => s + x.weight, 0);
  let r = Math.random() * total;
  for (const it of items) {
    r -= it.weight;
    if (r <= 0) return it.node;
  }
  return items[items.length - 1].node;
}

export function pickEdge(subject, rels, pack, profile) {
  const candidates = rels.filter(r =>
    r.source === subject.id
    && chapterOverlap(r.chapters, pack)
    && r.target.startsWith('entity:character_')   // target 也必須是人物
  );
  if (!candidates.length) return null;
  // 防重出：濾掉 profile.characters[subject.id].discoveredEdges 已含的
  const discovered = new Set(profile.characters[subject.id]?.discoveredEdges || []);
  const fresh = candidates.filter(r => !discovered.has(r.id));
  const pool = fresh.length ? fresh : candidates;
  return pool[Math.floor(Math.random() * pool.length)];
}

export function pickDistractors(correctNode, allNodes, edge, count = 3) {
  // 同 camp 但不同 relationType 對應的人物
  const sameCampOthers = allNodes.filter(n =>
    n.type === 'character'
    && n.camp === correctNode.camp
    && n.id !== correctNode.id
  );
  // 排除真實 edge 對應的 target（已是答案）
  const pool = sameCampOthers.filter(n => n.id !== edge.target);
  // 按 degree 由高到低取 count 個（孩子最容易混淆的）
  pool.sort((a, b) => b.degree - a.degree);
  return pool.slice(0, count);
}

export function buildQuestion({ subject, edge, allNodes, type, byId }) {
  const correctTarget = edge ? byId.get(edge.target) : null;
  if (type !== 'who-doesnt-belong' && !correctTarget) return null;
  let question;
  switch (type) {
    case 'who-is-this': {
      // 「下面哪一位 _ ? 跟 subject 的關係是 relationType」
      const distractors = pickDistractors(correctTarget, allNodes, edge);
      const choices = shuffle([correctTarget, ...distractors]);
      question = {
        type, subject, edge,
        prompt: `跟「${subject.name}」${edge.relationType}的是哪一位？`,
        clue: edge.description?.split('；')[0] || '',
        choices,
        correctChoiceId: correctTarget.id,
      };
      break;
    }
    case 'what-relation': {
      // 「subject 跟 correctTarget 是什麼關係？」
      const correctCategory = edge.category;
      const otherCategories = ['kinship', 'command', 'military', 'strategy']
        .filter(c => c !== correctCategory)
        .slice(0, 3);
      const allCats = shuffle([correctCategory, ...otherCategories]);
      question = {
        type, subject, edge,
        prompt: `「${subject.name}」跟「${correctTarget.name}」是什麼關係？`,
        clue: edge.description?.split('；')[0] || '',
        choices: allCats.map(c => ({ id: c, name: CATEGORY_DISPLAY[c] || c })),
        correctChoiceId: correctCategory,
      };
      break;
    }
    case 'who-doesnt-belong': {
      // 給 4 人，3 個同 camp，1 個不同
      const sameCamp = allNodes.filter(n =>
        n.type === 'character' && n.camp === subject.camp && n.id !== subject.id
      ).slice(0, 3);
      const otherCamp = allNodes.find(n =>
        n.type === 'character' && n.camp !== subject.camp && n.camp !== 'other' && n.isTrunk
      );
      if (!otherCamp || sameCamp.length < 3) return null;
      const choices = shuffle([...sameCamp, otherCamp]);
      question = {
        type, subject, edge: null,
        prompt: `下面哪一位不是「${CAMP_DISPLAY[subject.camp]}」？`,
        clue: '',
        choices,
        correctChoiceId: otherCamp.id,
      };
      break;
    }
    default:
      return null;
  }
  return question;
}

const CATEGORY_DISPLAY = {
  command: '主從／統率', military: '戰鬥／對戰',
  strategy: '計策／謀略', kinship: '親族／結拜',
  place: '同處', office: '官職', object: '物件',
  story: '同一段故事', other: '其他',
};

const CAMP_DISPLAY = {
  wei: '曹魏', shu: '劉蜀', wu: '東吳',
  lords: '群雄', mixed: '混合', other: '其他',
};

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function questionFingerprint(q) {
  return `${q.type}|${q.subject.id}|${q.edge?.id || ''}|${q.correctChoiceId}`;
}
