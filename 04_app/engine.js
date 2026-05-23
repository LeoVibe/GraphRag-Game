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

const QUESTION_TYPES = [
  'who-is-this',
  'what-relation',
  'who-doesnt-belong',
  'relation-chain',
  'personality-match',
];

export function chooseQuestionType(profile, subjectLevel = 0) {
  if (subjectLevel === 0) return 'who-is-this';
  if (subjectLevel === 1) {
    return Math.random() < 0.5 ? 'what-relation' : 'who-doesnt-belong';
  }
  const r = Math.random();
  if (subjectLevel >= 3 && r < 0.25) return 'personality-match';
  if (r < 0.35) return 'relation-chain';
  return ['who-is-this', 'what-relation', 'who-doesnt-belong'][Math.floor(Math.random() * 3)];
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

export function buildQuestion({
  subject,
  edge,
  allNodes,
  type,
  byId,
  personality = null,
  pack = null,
  rels = null,
  profile = null,
}) {
  const nodeIndex = byId || new Map((allNodes || []).map(n => [n.id, n]));
  const correctTarget = edge ? nodeIndex.get(edge.target) : null;
  if ((type === 'who-is-this' || type === 'what-relation') && !correctTarget) return null;
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
    case 'relation-chain': {
      question = buildRelationChainQuestion(subject, allNodes, rels, nodeIndex, profile);
      if (!question) return null;
      break;
    }
    case 'personality-match': {
      question = buildPersonalityMatchQuestion(allNodes, personality, profile, pack);
      if (!question) return null;
      break;
    }
    default:
      return null;
  }
  return question;
}

function buildRelationChainQuestion(subject, allNodes, rels, byId, profile) {
  if (!subject || !Array.isArray(rels) || !byId) return null;
  const characterIds = new Set((allNodes || [])
    .filter(n => n.type === 'character')
    .map(n => n.id));
  const subjectOutgoing = uniqueById(rels
    .filter(r => r.source === subject.id && characterIds.has(r.target) && r.target !== subject.id)
    .map(r => ({ edge: r, node: byId.get(r.target) }))
    .filter(x => x.node));
  if (subjectOutgoing.length < 4) return null;

  for (const candidate of shuffle(subjectOutgoing)) {
    const middleNode = candidate.node;
    const middleOutgoing = shuffle(rels.filter(r =>
      r.source === middleNode.id
      && characterIds.has(r.target)
      && r.target !== subject.id
      && r.target !== middleNode.id
    ));
    for (const secondEdge of middleOutgoing) {
      const endNode = byId.get(secondEdge.target);
      if (!endNode) continue;
      const pathIds = new Set([subject.id, middleNode.id, endNode.id]);
      const distractors = subjectOutgoing
        .map(x => x.node)
        .filter(n => !pathIds.has(n.id))
        .slice(0, 3);
      if (distractors.length < 3) continue;
      return {
        type: 'relation-chain',
        subject,
        edge: candidate.edge,
        secondEdge,
        middleNode,
        endNode,
        path: [subject.id, middleNode.id, endNode.id],
        prompt: `「${subject.name}」想找「${endNode.name}」說事，要經過誰才認得？`,
        clue: `${subject.name} 跟 ${middleNode.name} ${candidate.edge.relationType}；${middleNode.name} 跟 ${endNode.name} ${secondEdge.relationType}。`,
        choices: shuffle([middleNode, ...distractors]),
        correctChoiceId: middleNode.id,
      };
    }
  }
  return null;
}

function buildPersonalityMatchQuestion(allNodes, personality, profile, pack) {
  if (!Array.isArray(allNodes) || !personality) return null;
  const candidates = allNodes.filter(n =>
    n.type === 'character'
    && n.isTrunk
    && (!pack || chapterOverlap(n.chapters, pack))
    && Array.isArray(personality[n.id]?.traits)
    && personality[n.id].traits.length > 0
  );
  if (candidates.length < 4) return null;

  const usedTraits = new Set();
  const picked = [];
  for (const node of shuffle(candidates)) {
    const traitLabel = personality[node.id].traits.find(t => !usedTraits.has(t));
    if (!traitLabel) continue;
    usedTraits.add(traitLabel);
    picked.push({ node, traitLabel });
    if (picked.length === 4) break;
  }
  if (picked.length < 4) return null;

  return {
    type: 'personality-match',
    subject: picked[0].node,
    edge: null,
    prompt: '把每個個性敘述拖到對應的人物身上',
    clue: '',
    choices: shuffle(picked.map(({ node, traitLabel }) => ({
      id: node.id,
      name: node.name,
      traitLabel,
    }))),
    correctChoiceId: 'matched',
    matchPairs: picked.map(({ node, traitLabel }) => ({
      characterId: node.id,
      traitLabel,
    })),
  };
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

function uniqueById(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const id = item.node?.id || item.id;
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push(item);
  }
  return result;
}

export function questionFingerprint(q) {
  return `${q.type}|${q.subject.id}|${q.edge?.id || ''}|${q.correctChoiceId}`;
}
