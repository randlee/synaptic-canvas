import DefaultTheme from 'vitepress/theme'
import PluginFlowVisualizer from './components/PluginFlowVisualizer.vue'
import DetailPanel from './components/DetailPanel.vue'
import TestComponent from './components/TestComponent.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // Register global components
    app.component('PluginFlowVisualizer', PluginFlowVisualizer)
    app.component('DetailPanel', DetailPanel)
    app.component('TestComponent', TestComponent)
  }
}
