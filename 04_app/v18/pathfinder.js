import { data } from './data.js';

export function shortestPath(fromId, toId, maxHops) {
  if (fromId === toId) return { nodes: [fromId], edges: [] };
  const queue = [{ id: fromId, nodes: [fromId], edges: [] }];
  const seen = new Set([fromId]);
  while (queue.length) {
    const current = queue.shift();
    if (current.edges.length >= maxHops) continue;
    for (const next of data.adjacency.get(current.id) || []) {
      if (seen.has(next.to)) continue;
      const nodes = current.nodes.concat(next.to);
      const edges = current.edges.concat(next.rel);
      if (next.to === toId) return { nodes, edges };
      seen.add(next.to);
      queue.push({ id: next.to, nodes, edges });
    }
  }
  return null;
}

export function segmentTag(rel) {
  if (['military', 'strategy'].includes(rel.category)) return { className: 'military', label: '軍事' };
  if (['kinship', 'office', 'command'].includes(rel.category)) return { className: 'identity', label: '身分' };
  return { className: 'interact', label: '互動' };
}
