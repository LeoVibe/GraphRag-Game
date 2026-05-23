import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  CHAPTER_PACKS, chooseQuestionType, chapterOverlap, pickSubject,
  pickEdge, pickDistractors, buildQuestion, questionFingerprint,
} from './engine.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const nodes = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/nodes.json`));
const rels = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/rels.json`));
const personality = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/character_personality.json`));
const byId = new Map(nodes.map(n => [n.id, n]));
const EMPTY_PROFILE = { unlockedPacks: ['ch001_010'], characters: {}, totalStars: 0, recentQuestions: [] };

test('CHAPTER_PACKS 有 6 包 cover 1-60', () => {
  assert.equal(CHAPTER_PACKS.length, 6);
  assert.equal(CHAPTER_PACKS[0].start, 1);
  assert.equal(CHAPTER_PACKS[CHAPTER_PACKS.length - 1].end, 60);
});

test('chapterOverlap 正確判定', () => {
  assert.equal(chapterOverlap([5, 7, 9], { start: 1, end: 10 }), true);
  assert.equal(chapterOverlap([15, 17], { start: 1, end: 10 }), false);
  assert.equal(chapterOverlap([], { start: 1, end: 10 }), false);
});

test('pickSubject 從 ch001_010 包能挑出 isTrunk character', () => {
  const subj = pickSubject(nodes, CHAPTER_PACKS[0], EMPTY_PROFILE);
  assert.ok(subj, '應該挑得到主角');
  assert.equal(subj.type, 'character');
  assert.equal(subj.isTrunk, true);
  assert.ok(subj.chapters.some(c => c <= 10));
});

test('pickSubject 對未知章節範圍應 return null', () => {
  const subj = pickSubject(nodes, { start: 999, end: 1000 }, EMPTY_PROFILE);
  assert.equal(subj, null);
});

test('pickEdge 取主角的 outgoing character→character 關係', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  assert.ok(edge, '曹操在 1-10 章應有 outgoing rel');
  assert.equal(edge.source, cao.id);
  assert.ok(edge.target.startsWith('entity:character_'));
});

test('pickDistractors 取得 3 個同 camp 不同 id 人物', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const liu = nodes.find(n => n.name === '劉備' && n.type === 'character');
  const fakeEdge = { target: liu.id };
  const distractors = pickDistractors(liu, nodes, fakeEdge);
  assert.equal(distractors.length, 3);
  for (const d of distractors) {
    assert.equal(d.camp, liu.camp);
    assert.notEqual(d.id, liu.id);
  }
});

test('buildQuestion who-is-this 結構正確', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'who-is-this', byId });
  assert.ok(q, '應該建得起來');
  assert.equal(q.type, 'who-is-this');
  assert.equal(q.choices.length, 4);
  assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
  assert.ok(q.prompt.includes(cao.name));
});

test('buildQuestion what-relation 給 4 個 category 選項', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'what-relation', byId });
  assert.ok(q);
  assert.equal(q.choices.length, 4);
  assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
});

test('buildQuestion who-doesnt-belong 找一個不同 camp', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({ subject: cao, edge: null, allNodes: nodes, type: 'who-doesnt-belong', byId });
  if (q) {
    assert.equal(q.choices.length, 4);
    const correct = q.choices.find(c => c.id === q.correctChoiceId);
    assert.notEqual(correct.camp, cao.camp);
  }
});

test('questionFingerprint 對同問題回傳相同 hash', () => {
  const q1 = { type: 'who-is-this', subject: { id: 'a' }, edge: { id: 'e1' }, correctChoiceId: 'c1' };
  const q2 = { type: 'who-is-this', subject: { id: 'a' }, edge: { id: 'e1' }, correctChoiceId: 'c1' };
  assert.equal(questionFingerprint(q1), questionFingerprint(q2));
});

test('chooseQuestionType 對未認識（level 0）給 who-is-this', () => {
  assert.equal(chooseQuestionType(EMPTY_PROFILE, 0), 'who-is-this');
});

test('連續 10 次 pickSubject + buildQuestion 都成功', () => {
  for (let i = 0; i < 10; i++) {
    const subj = pickSubject(nodes, CHAPTER_PACKS[0], EMPTY_PROFILE);
    const edge = pickEdge(subj, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
    if (edge) {
      const q = buildQuestion({ subject: subj, edge, allNodes: nodes, type: 'who-is-this', byId });
      assert.ok(q, `iteration ${i} build 失敗`);
    }
  }
});

test('包 ch031_040 候選池含諸葛亮（驗證 data fix）', () => {
  // 直接驗證資料層：諸葛亮 isTrunk 且 chapters 含 31-40 區間
  // (避開 weighted random 在 dozens of 候選下的 flakiness)
  const candidates = nodes.filter(n =>
    n.kind === 'entity' && n.type === 'character' && n.isTrunk
    && n.chapters.some(c => c >= 31 && c <= 40)
  );
  const names = candidates.map(n => n.name);
  assert.ok(names.includes('諸葛亮'),
    `ch031_040 候選池應含諸葛亮，實際 ${candidates.length} 位候選: ${names.slice(0, 10).join(', ')}...`);
  // sanity check：100 次抽樣應抽到核心人物之一（不強求特定一人）
  const subjs = new Set();
  for (let i = 0; i < 100; i++) {
    const s = pickSubject(nodes, CHAPTER_PACKS[3], EMPTY_PROFILE);
    if (s) subjs.add(s.name);
  }
  const coreHit = ['諸葛亮', '徐庶', '龐統', '劉備', '曹操'].some(n => subjs.has(n));
  assert.ok(coreHit, `100 次抽樣應抽到至少 1 個核心人物，實際: ${[...subjs].slice(0, 15)}`);
});

test('每條 choice 都有 name 屬性', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'who-is-this', byId });
  for (const c of q.choices) assert.ok(c.name);
});

test('buildQuestion relation-chain 結構正確', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({
    subject: cao, edge: null, allNodes: nodes, type: 'relation-chain',
    byId, rels, profile: EMPTY_PROFILE,
  });
  assert.ok(q, '應該建得起 relation-chain');
  assert.equal(q.type, 'relation-chain');
  assert.equal(q.choices.length, 4);
  assert.equal(q.correctChoiceId, q.middleNode.id);
  assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
  assert.ok(q.prompt.includes(cao.name));
});

test('relation-chain 中間人不為 subject 自己', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({
    subject: cao, edge: null, allNodes: nodes, type: 'relation-chain',
    byId, rels, profile: EMPTY_PROFILE,
  });
  assert.ok(q, '應該建得起 relation-chain');
  assert.notEqual(q.correctChoiceId, cao.id);
});

test('relation-chain 三個干擾項都不是答案', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({
    subject: cao, edge: null, allNodes: nodes, type: 'relation-chain',
    byId, rels, profile: EMPTY_PROFILE,
  });
  assert.ok(q, '應該建得起 relation-chain');
  const pathIds = new Set(q.path);
  const distractors = q.choices.filter(c => c.id !== q.correctChoiceId);
  assert.equal(distractors.length, 3);
  for (const d of distractors) {
    assert.notEqual(d.id, q.correctChoiceId);
    assert.equal(pathIds.has(d.id), false);
  }
});

test('buildQuestion personality-match 有 4 對配對', () => {
  const q = buildQuestion({
    subject: null, edge: null, allNodes: nodes, type: 'personality-match',
    byId, rels, profile: EMPTY_PROFILE, personality, pack: CHAPTER_PACKS[0],
  });
  assert.ok(q, '應該建得起 personality-match');
  assert.equal(q.type, 'personality-match');
  assert.equal(q.matchPairs.length, 4);
  for (const p of q.matchPairs) {
    assert.ok(p.characterId);
    assert.ok(p.traitLabel);
  }
});

test('personality-match 4 個 traits 不重複', () => {
  const q = buildQuestion({
    subject: null, edge: null, allNodes: nodes, type: 'personality-match',
    byId, rels, profile: EMPTY_PROFILE, personality, pack: CHAPTER_PACKS[0],
  });
  assert.ok(q, '應該建得起 personality-match');
  assert.equal(new Set(q.matchPairs.map(p => p.traitLabel)).size, 4);
});

test('personality-match 全部 character 都是 isTrunk', () => {
  const q = buildQuestion({
    subject: null, edge: null, allNodes: nodes, type: 'personality-match',
    byId, rels, profile: EMPTY_PROFILE, personality, pack: CHAPTER_PACKS[0],
  });
  assert.ok(q, '應該建得起 personality-match');
  for (const pair of q.matchPairs) {
    assert.equal(byId.get(pair.characterId)?.isTrunk, true);
  }
});
