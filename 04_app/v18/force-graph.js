export function renderForceGraph(container, nodes, links, options = {}) {
  container.innerHTML = '';
  const {
    width = container.clientWidth || 400,
    height = container.clientHeight || 300,
    onNodeClick,
    linkDistance = 80
  } = options;

  const svg = d3.select(container).append('svg')
    .attr('class', 'force-svg')
    .attr('width', width).attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`);

  const fixedPositions = new Map(nodes
    .filter(node => node.fx != null || node.fy != null)
    .map(node => [node, { fx: node.fx, fy: node.fy }]));

  // 陣營分群：把 wei/shu/wu/lords 分配到四個象限，加 cluster force 把同陣營吸在一起
  const clusterCenters = {
    wei:   { x: width * 0.78, y: height * 0.30 },  // 右上
    shu:   { x: width * 0.22, y: height * 0.30 },  // 左上
    wu:    { x: width * 0.50, y: height * 0.82 },  // 下中
    lords: { x: width * 0.88, y: height * 0.72 },  // 右下
    mixed: { x: width * 0.12, y: height * 0.72 },  // 左下
  };

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(linkDistance))
    .force('charge', d3.forceManyBody().strength(-220))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.05))
    .force('collision', d3.forceCollide().radius(36))
    .force('cluster', clusterForce(clusterCenters, 0.18));

  function clusterForce(centers, strength) {
    return function(alpha) {
      for (const node of nodes) {
        if (node.isFocus || node.isBattleCenter) continue;
        if (node.fx != null || node.fy != null) continue;
        const center = centers[node.camp];
        if (!center) continue;
        node.vx -= (node.x - center.x) * alpha * strength;
        node.vy -= (node.y - center.y) * alpha * strength;
      }
    };
  }

  // 連線：依 category 染色 + 依 weight 加粗，讓不同人物的圖譜長相差異化
  const linkLayer = svg.append('g').attr('class', 'force-links');
  const link = linkLayer.selectAll('line').data(links).join('line')
    .attr('class', d => `force-link cat-${d.category || 'other'}`)
    .attr('stroke-width', d => {
      const w = d.weight || 1;
      return Math.min(4, 1.5 + Math.log2(w + 1) * 0.8);
    });

  // 連線文字 label（關係動詞），力導圖跑後沿線中點顯示
  const linkLabel = svg.append('g').attr('class', 'force-link-labels')
    .selectAll('text').data(links.filter(l => l.label)).join('text')
    .attr('class', 'force-link-label')
    .attr('text-anchor', 'middle')
    .attr('dy', -2)
    .text(d => d.label);

  const node = svg.append('g').attr('class', 'force-nodes')
    .selectAll('g').data(nodes).join('g')
    .attr('class', d => ['force-node', d.isFocus ? 'is-focus' : '', d.isBattleCenter ? 'battle-center' : ''].join(' ').trim())
    .attr('data-camp', d => d.camp || 'other')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.fx ?? d.x;
        d.fy = d.fy ?? d.y;
      })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        const fixed = fixedPositions.get(d);
        d.fx = fixed ? fixed.fx : null;
        d.fy = fixed ? fixed.fy : null;
      })
    );

  node.append('rect').attr('rx', 14).attr('ry', 14);
  node.append('text').attr('text-anchor', 'middle').attr('dy', '0.35em').text(d => d.name);

  // size rects after text is in DOM
  node.each(function() {
    const textEl = d3.select(this).select('text').node();
    const bbox = textEl.getBBox();
    d3.select(this).select('rect')
      .attr('x', -bbox.width / 2 - 14).attr('y', -bbox.height / 2 - 6)
      .attr('width', bbox.width + 28).attr('height', bbox.height + 12);
  });

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  if (onNodeClick) {
    node.on('click', (event, d) => { if (!event.defaultPrevented) onNodeClick(d, event); });
  }

  return { simulation, svg, destroy() { simulation.stop(); container.innerHTML = ''; } };
}
