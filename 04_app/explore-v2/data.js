const NODES_URL = new URL('../../03_graphrag/nodes.json', import.meta.url);
const RELS_URL = new URL('../../03_graphrag/rels.json', import.meta.url);
const PERSONALITY_URL = new URL('../../03_graphrag/character_personality.json', import.meta.url);

export const DATA_URLS = {
  nodes: NODES_URL,
  rels: RELS_URL,
  personality: PERSONALITY_URL
};

export const data = {
  nodes: [],
  rels: [],
  personality: {},
  byId: new Map(),
  charByName: new Map(),
  nodeByName: new Map(),
  characters: [],
  trunkCharacters: [],
  charCharRels: [],
  outgoing: new Map(),
  adjacency: new Map()
};

export async function loadData() {
  const [nodes, rels, personality] = await Promise.all([
    fetchJson(NODES_URL),
    fetchJson(RELS_URL),
    fetchJson(PERSONALITY_URL)
  ]);
  data.nodes = nodes;
  data.rels = rels;
  data.personality = personality;
  buildIndexes();
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

export function buildIndexes() {
  data.byId = new Map(data.nodes.map(node => [node.id, node]));
  data.nodeByName = new Map();
  for (const node of data.nodes) {
    if (!data.nodeByName.has(node.name)) data.nodeByName.set(node.name, node);
  }
  data.characters = data.nodes.filter(node => node.type === 'character');
  data.charByName = new Map(data.characters.map(node => [node.name, node]));
  data.trunkCharacters = data.characters
    .filter(node => node.isTrunk)
    .sort((a, b) => (b.degree || 0) - (a.degree || 0))
    .slice(0, 30);
  data.charCharRels = data.rels.filter(rel => isCharacterId(rel.source) && isCharacterId(rel.target));
  data.outgoing = groupBy(data.rels, rel => rel.source);
  data.adjacency = new Map();
  for (const rel of data.charCharRels) {
    if (!data.adjacency.has(rel.source)) data.adjacency.set(rel.source, []);
    data.adjacency.get(rel.source).push({ to: rel.target, rel });
  }
  for (const items of data.adjacency.values()) {
    items.sort((a, b) => (b.rel.weight || 0) - (a.rel.weight || 0));
  }
}

export function resolveCharacterId(value) {
  if (!value) return '';
  const raw = decodeURIComponent(String(value));
  if (data.byId.get(raw)?.type === 'character') return raw;
  const prefixed = `entity:character_${raw}`;
  if (data.byId.get(prefixed)?.type === 'character') return prefixed;
  return data.charByName.get(raw)?.id || '';
}

export function resolveAnyId(value) {
  if (!value) return '';
  const raw = String(value);
  if (data.byId.has(raw)) return raw;
  if (data.nodeByName.has(raw)) return data.nodeByName.get(raw).id;
  if (data.nodeByName.has(`${raw}勢力`)) return data.nodeByName.get(`${raw}勢力`).id;
  const character = resolveCharacterId(raw);
  if (character) return character;
  const fuzzy = data.nodes.find(node => node.name.includes(raw) || raw.includes(node.name));
  return fuzzy?.id || '';
}

export function resolveAnyNode(value) {
  return data.byId.get(resolveAnyId(value));
}

export function isCharacterId(id) {
  return typeof id === 'string' && id.startsWith('entity:character_');
}

export function groupBy(items, keyFn) {
  const map = new Map();
  for (const item of items) {
    const key = keyFn(item);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(item);
  }
  return map;
}

export function mergeRels(primary, secondary) {
  const seen = new Set(primary.map(rel => rel.id));
  const merged = [...primary];
  for (const rel of secondary) {
    if (seen.has(rel.id)) continue;
    seen.add(rel.id);
    merged.push(rel);
  }
  return merged;
}

export function campKey(node) {
  const camp = node?.camp;
  if (['wei', 'shu', 'wu', 'lords'].includes(camp)) return camp;
  if (camp === 'mixed') return 'lords';
  return 'other';
}

export function nodeName(id) {
  return data.byId.get(id)?.name || id || '';
}

export function avatar(name) {
  return [...String(name || '?')][0] || '?';
}

export function firstSentence(text) {
  const part = splitDescription(text)[0] || '';
  return part.length > 42 ? `${part.slice(0, 42)}...` : part;
}

export function splitDescription(text) {
  return String(text || '').split('；').map(item => item.trim()).filter(Boolean);
}

export function chapterForNodeSegment(node, index) {
  const chapter = (node.chapters || [])[index] || (node.chapterStart ? node.chapterStart + index : '');
  return chapter ? `第 ${chapter} 回` : chapterRangeLabel(node);
}

export function chapterRangeLabel(item) {
  if (!item) return '章回未知';
  if (item.chapterStart && item.chapterEnd && item.chapterStart !== item.chapterEnd) return `第 ${item.chapterStart}-${item.chapterEnd} 回`;
  const chapter = item.chapterStart || item.chapterEnd || (item.chapters || [])[0];
  return chapter ? `第 ${chapter} 回` : '章回未知';
}

export function chapterLabel(rel) {
  if (!rel) return '章回未知';
  if (rel.chapterStart && rel.chapterEnd && rel.chapterStart !== rel.chapterEnd) return `第 ${rel.chapterStart}-${rel.chapterEnd} 回`;
  const chapter = rel.chapterStart || rel.chapterEnd || (rel.chapters || [])[0];
  return chapter ? `第 ${chapter} 回` : '章回未知';
}

export function sharedChapters(path) {
  const all = new Set();
  for (const rel of path.edges) {
    for (const ch of rel.chapters || []) all.add(ch);
  }
  return all.size;
}

export function lineAttrs(x1, y1, x2, y2) {
  return `x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"`;
}

// 舊 div-based lineStyle 已棄用：% 對角線在非正方形 canvas 上不對齊。
// 新方案：用 SVG <line> + viewBox 100×100 + preserveAspectRatio="none"，
// 線自然會接到節點位置（節點用 left/top % 同樣 100 為基準）。
// 留 lineStyle 作 alias 以防遺漏 import，但不該再用。
export function lineStyle() { return ''; }

export function range(start, end) {
  return Array.from({ length: Math.max(0, end - start + 1) }, (_, index) => start + index);
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

export function escapeAttr(value) {
  return escapeHtml(value);
}
