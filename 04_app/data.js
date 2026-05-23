const DATA_BASE = '../03_graphrag';
let cache = null;

export async function loadData() {
  if (cache) return cache;
  const [nodes, rels, personality] = await Promise.all([
    fetch(`${DATA_BASE}/nodes.json`).then(r => r.json()),
    fetch(`${DATA_BASE}/rels.json`).then(r => r.json()),
    fetch(`${DATA_BASE}/character_personality.json`).then(r => r.json()),
  ]);
  cache = { nodes, rels, personality };
  return cache;
}

// helpers used elsewhere
export function indexNodes(nodes) {
  const byId = new Map();
  const byName = new Map();
  for (const n of nodes) {
    byId.set(n.id, n);
    byName.set(n.name, n);
  }
  return { byId, byName };
}

export function indexRelsBySource(rels) {
  const map = new Map();
  for (const r of rels) {
    if (!map.has(r.source)) map.set(r.source, []);
    map.get(r.source).push(r);
  }
  return map;
}
