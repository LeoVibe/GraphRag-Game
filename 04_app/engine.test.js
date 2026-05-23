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

test('包 ch031_040 能挑出諸葛亮（驗證 data fix）', () => {
  const subjs = [];
  for (let i = 0; i < 50; i++) {
    const s = pickSubject(nodes, CHAPTER_PACKS[3], EMPTY_PROFILE);
    if (s) subjs.push(s.name);
  }
  // 50 次抽取應該至少有一次抽到諸葛亮（他 isTrunk 且 chapters 含 36+）
  assert.ok(subjs.includes('諸葛亮'), `50 次抽樣應含諸葛亮，實際: ${[...new Set(subjs)]}`);
});

test('每條 choice 都有 name 屬性', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'who-is-this', byId });
  for (const c of q.choices) assert.ok(c.name);
});
