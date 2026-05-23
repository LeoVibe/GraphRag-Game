import { data } from './data.js';

/**
 * BFS 找最短路徑。預設 minHops=2（必經中間人），找不到才 fallback 1 跳。
 * 「兩個人怎麼認識」的教學意涵：透過中間人連起來才有價值，
 * 直接認識就是「他們本來就認識」沒中間人可看，學不到網絡概念。
 */
export function shortestPath(fromId, toId, maxHops = 3, minHops = 2) {
  if (fromId === toId) return { nodes: [fromId], edges: [] };
  // 先找 minHops 及以上跳數的路徑
  const path = bfs(fromId, toId, maxHops, minHops);
  if (path) return path;
  // 找不到，fallback 接受 1 跳（標記為直接認識）
  if (minHops > 1) {
    const direct = bfs(fromId, toId, maxHops, 1);
    if (direct) return { ...direct, directlyConnected: true };
  }
  return null;
}

function bfs(fromId, toId, maxHops, minHops) {
  // seen 改成「每個 path 各自帶 visited」避免 1 跳到 target 後阻擋 2 跳路徑被找到。
  // 如果用 global seen，會發生「諸葛亮→曹操」1 跳先 mark 曹操，導致
  // 「諸葛亮→劉備→曹操」2 跳路徑永遠不可達。
  const queue = [{ id: fromId, nodes: [fromId], edges: [], visited: new Set([fromId]) }];
  while (queue.length) {
    const current = queue.shift();
    if (current.edges.length >= maxHops) continue;
    for (const next of data.adjacency.get(current.id) || []) {
      if (current.visited.has(next.to)) continue;
      const nodes = current.nodes.concat(next.to);
      const edges = current.edges.concat(next.rel);
      if (next.to === toId && edges.length >= minHops) return { nodes, edges };
      const visited = new Set(current.visited);
      visited.add(next.to);
      queue.push({ id: next.to, nodes, edges, visited });
    }
  }
  return null;
}

export function segmentTag(rel) {
  if (['military', 'strategy'].includes(rel.category)) return { className: 'military', label: '軍事' };
  if (['kinship', 'office', 'command'].includes(rel.category)) return { className: 'identity', label: '身分' };
  return { className: 'interact', label: '互動' };
}
