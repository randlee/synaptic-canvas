<script setup lang="ts">
import { ref, onMounted, watch, computed, onUnmounted } from 'vue'

// Dynamic import to avoid SSR issues
let d3: typeof import('d3') | null = null

// Props
interface Node {
  id: string
  label: string
  subtitle?: string
  type: 'entry' | 'agent' | 'gate' | 'success' | 'error'
  x?: number
  y?: number
  details?: {
    description?: string
    input?: object
    output?: object
    context?: string[]
    gatePrompt?: object
    gateResponse?: object
    skipCondition?: string
    errorCodes?: Array<{ code: string; recoverable: boolean; action: string }>
  }
}

interface Edge {
  from: string
  to: string
  label?: string
}

interface Props {
  pluginName: string
  nodes: Node[]
  edges: Edge[]
}

const props = defineProps<Props>()

// State
const svgRef = ref<SVGSVGElement | null>(null)
const selectedNode = ref<Node | null>(null)
const containerWidth = ref(800)
const isLoaded = ref(false)

// Layout configuration
const nodeWidth = 160
const nodeHeight = 60
const levelHeight = 120
const horizontalSpacing = 200

// Computed layout positions
const layoutNodes = computed(() => {
  // Simple hierarchical layout
  const levels: Map<string, number> = new Map()
  const positions: Map<string, { x: number; y: number }> = new Map()

  // BFS to determine levels
  const visited = new Set<string>()
  const queue: Array<{ id: string; level: number }> = []

  // Find entry nodes
  const incomingEdges = new Set(props.edges.map(e => e.to))
  props.nodes.forEach(node => {
    if (!incomingEdges.has(node.id) || node.type === 'entry') {
      queue.push({ id: node.id, level: 0 })
    }
  })

  while (queue.length > 0) {
    const { id, level } = queue.shift()!
    if (visited.has(id)) continue
    visited.add(id)
    levels.set(id, level)

    // Find children
    props.edges
      .filter(e => e.from === id)
      .forEach(e => {
        if (!visited.has(e.to)) {
          queue.push({ id: e.to, level: level + 1 })
        }
      })
  }

  // Count nodes per level
  const nodesPerLevel: Map<number, string[]> = new Map()
  levels.forEach((level, id) => {
    if (!nodesPerLevel.has(level)) {
      nodesPerLevel.set(level, [])
    }
    nodesPerLevel.get(level)!.push(id)
  })

  // Calculate positions
  const centerX = containerWidth.value / 2
  nodesPerLevel.forEach((nodeIds, level) => {
    const totalWidth = nodeIds.length * horizontalSpacing
    const startX = centerX - totalWidth / 2 + horizontalSpacing / 2

    nodeIds.forEach((id, index) => {
      positions.set(id, {
        x: startX + index * horizontalSpacing,
        y: 80 + level * levelHeight
      })
    })
  })

  return props.nodes.map(node => ({
    ...node,
    x: positions.get(node.id)?.x ?? 400,
    y: positions.get(node.id)?.y ?? 100
  }))
})

// D3 rendering
onMounted(async () => {
  // Dynamically import D3 to avoid SSR issues
  d3 = await import('d3')
  isLoaded.value = true
  renderDiagram()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function handleResize() {
  if (svgRef.value) {
    containerWidth.value = svgRef.value.parentElement?.clientWidth ?? 800
    renderDiagram()
  }
}

watch(() => props.nodes, renderDiagram, { deep: true })
watch(() => props.edges, renderDiagram, { deep: true })

function renderDiagram() {
  if (!svgRef.value || !d3) return

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  // Define arrow marker
  svg.append('defs')
    .append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 8)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#64748b')

  // Calculate SVG height
  const maxY = Math.max(...layoutNodes.value.map(n => n.y ?? 0))
  svg.attr('viewBox', `0 0 ${containerWidth.value} ${maxY + 100}`)

  // Create edges
  const edgeGroup = svg.append('g').attr('class', 'edges')

  props.edges.forEach(edge => {
    const fromNode = layoutNodes.value.find(n => n.id === edge.from)
    const toNode = layoutNodes.value.find(n => n.id === edge.to)

    if (!fromNode || !toNode) return

    const startX = fromNode.x!
    const startY = fromNode.y! + nodeHeight / 2
    const endX = toNode.x!
    const endY = toNode.y! - nodeHeight / 2 - 8

    // Draw curved path
    const midY = (startY + endY) / 2
    const path = `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`

    edgeGroup.append('path')
      .attr('class', 'flow-edge')
      .attr('d', path)

    // Edge label
    if (edge.label) {
      edgeGroup.append('text')
        .attr('class', 'edge-label')
        .attr('x', (startX + endX) / 2)
        .attr('y', midY - 5)
        .text(edge.label)
    }
  })

  // Create nodes
  const nodeGroup = svg.append('g').attr('class', 'nodes')

  layoutNodes.value.forEach(node => {
    const g = nodeGroup.append('g')
      .attr('class', `flow-node ${node.type}${selectedNode.value?.id === node.id ? ' selected' : ''}`)
      .attr('transform', `translate(${node.x! - nodeWidth / 2}, ${node.y! - nodeHeight / 2})`)
      .style('cursor', 'pointer')
      .on('click', () => selectNode(node))

    // Node rectangle
    g.append('rect')
      .attr('width', nodeWidth)
      .attr('height', nodeHeight)

    // Node label
    g.append('text')
      .attr('x', nodeWidth / 2)
      .attr('y', node.subtitle ? nodeHeight / 2 - 8 : nodeHeight / 2)
      .text(node.label)

    // Subtitle
    if (node.subtitle) {
      g.append('text')
        .attr('class', 'node-subtitle')
        .attr('x', nodeWidth / 2)
        .attr('y', nodeHeight / 2 + 10)
        .text(node.subtitle)
    }

    // Gate indicator (diamond icon for gates)
    if (node.type === 'gate') {
      g.append('text')
        .attr('x', nodeWidth / 2)
        .attr('y', nodeHeight - 8)
        .attr('text-anchor', 'middle')
        .attr('font-size', '10px')
        .attr('fill', '#a855f7')
        .text('User Decision')
    }
  })
}

function selectNode(node: Node) {
  if (selectedNode.value?.id === node.id) {
    selectedNode.value = null
  } else {
    selectedNode.value = node
  }
  renderDiagram()
}

function closeDetails() {
  selectedNode.value = null
  renderDiagram()
}

// Expose for template
defineExpose({ selectedNode, closeDetails })
</script>

<template>
  <div class="plugin-flow-container">
    <div class="plugin-flow-header">
      <h3>{{ pluginName }} - Workflow Overview</h3>
      <div class="plugin-flow-legend">
        <div class="legend-item">
          <span class="legend-dot entry"></span>
          <span>Entry</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot agent"></span>
          <span>Agent</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot gate"></span>
          <span>User Gate</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot success"></span>
          <span>Success</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot error"></span>
          <span>Error</span>
        </div>
      </div>
    </div>

    <div v-if="!isLoaded" style="padding: 2rem; text-align: center; color: var(--vp-c-text-2);">
      Loading diagram...
    </div>
    <svg v-show="isLoaded" ref="svgRef" class="plugin-flow-svg" preserveAspectRatio="xMidYMid meet"></svg>

    <DetailPanel
      v-if="selectedNode"
      :node="selectedNode"
      @close="closeDetails"
    />
  </div>
</template>
