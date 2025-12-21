<script setup lang="ts">
import { ref } from 'vue'

interface NodeDetails {
  description?: string
  input?: object
  output?: object
  context?: string[]
  gatePrompt?: object
  gateResponse?: object
  skipCondition?: string
  errorCodes?: Array<{ code: string; recoverable: boolean; action: string }>
}

interface Node {
  id: string
  label: string
  subtitle?: string
  type: 'entry' | 'agent' | 'gate' | 'success' | 'error'
  details?: NodeDetails
}

interface Props {
  node: Node
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const activeTab = ref<'overview' | 'input' | 'output' | 'context' | 'errors'>('overview')

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'input', label: 'Input Schema' },
  { id: 'output', label: 'Output Schema' },
  { id: 'context', label: 'Context Added' },
  { id: 'errors', label: 'Error Handling' }
]

function getNodeTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    entry: 'Entry Point',
    agent: 'Agent',
    gate: 'User Decision Gate',
    success: 'Success State',
    error: 'Error State'
  }
  return labels[type] ?? type
}

function formatJson(obj: object | undefined): string {
  if (!obj) return 'N/A'
  return JSON.stringify(obj, null, 2)
}
</script>

<template>
  <div class="detail-panel expanded">
    <div class="detail-panel-header">
      <h4>
        <span :class="`legend-dot ${node.type}`" style="display: inline-block;"></span>
        {{ node.label }}
        <span style="font-weight: 400; color: var(--vp-c-text-2); font-size: 0.85rem;">
          — {{ getNodeTypeLabel(node.type) }}
        </span>
      </h4>
      <button class="detail-panel-close" @click="emit('close')" aria-label="Close details">
        ✕
      </button>
    </div>

    <div class="detail-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="detail-tab"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id as typeof activeTab"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="detail-content">
      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'">
        <p v-if="node.details?.description">{{ node.details.description }}</p>
        <p v-else>
          <em>No description provided for this {{ getNodeTypeLabel(node.type).toLowerCase() }}.</em>
        </p>

        <template v-if="node.type === 'gate'">
          <h5>Gate Prompt</h5>
          <pre><code>{{ formatJson(node.details?.gatePrompt) }}</code></pre>

          <h5>Expected Response</h5>
          <pre><code>{{ formatJson(node.details?.gateResponse) }}</code></pre>

          <p v-if="node.details?.skipCondition">
            <strong>Skip Condition:</strong> <code>{{ node.details.skipCondition }}</code>
          </p>
        </template>
      </div>

      <!-- Input Schema Tab -->
      <div v-if="activeTab === 'input'">
        <template v-if="node.details?.input">
          <h5>Input Schema</h5>
          <pre><code>{{ formatJson(node.details.input) }}</code></pre>
        </template>
        <p v-else>
          <em>No input schema defined.</em>
        </p>
      </div>

      <!-- Output Schema Tab -->
      <div v-if="activeTab === 'output'">
        <template v-if="node.details?.output">
          <h5>Output Schema</h5>
          <pre><code>{{ formatJson(node.details.output) }}</code></pre>
        </template>
        <p v-else>
          <em>No output schema defined.</em>
        </p>
      </div>

      <!-- Context Tab -->
      <div v-if="activeTab === 'context'">
        <template v-if="node.details?.context && node.details.context.length > 0">
          <p>This {{ getNodeTypeLabel(node.type).toLowerCase() }} adds the following to the workflow context:</p>
          <div style="margin-top: 0.75rem;">
            <span
              v-for="ctx in node.details.context"
              :key="ctx"
              class="context-badge"
            >
              {{ ctx }}
            </span>
          </div>
        </template>
        <p v-else>
          <em>No context additions at this stage.</em>
        </p>
      </div>

      <!-- Errors Tab -->
      <div v-if="activeTab === 'errors'">
        <template v-if="node.details?.errorCodes && node.details.errorCodes.length > 0">
          <table class="schema-table">
            <thead>
              <tr>
                <th>Error Code</th>
                <th>Recoverable</th>
                <th>Suggested Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="err in node.details.errorCodes" :key="err.code">
                <td><code>{{ err.code }}</code></td>
                <td>{{ err.recoverable ? 'Yes' : 'No' }}</td>
                <td>{{ err.action }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        <p v-else>
          <em>No specific error codes documented for this stage.</em>
        </p>
      </div>
    </div>
  </div>
</template>
