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

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(linkDistance))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(36));

  const link = svg.append('g').attr('class', 'force-links')
    .selectAll('line').data(links).join('line');

  const node = svg.append('g').attr('class', 'force-nodes')
    .selectAll('g').data(nodes).join('g')
    .attr('class', d => ['force-node', d.isFocus ? 'is-focus' : '', d.isBattleCenter ? 'battle-center' : ''].join(' ').trim())
    .attr('data-camp', d => d.camp || 'other')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
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
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  if (onNodeClick) {
    node.on('click', (event, d) => { if (!event.defaultPrevented) onNodeClick(d, event); });
  }

  return { simulation, svg, destroy() { simulation.stop(); container.innerHTML = ''; } };
}
