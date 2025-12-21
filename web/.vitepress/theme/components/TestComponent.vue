<script setup>
import { ref } from 'vue'
const count = ref(0)
</script>

<template>
  <div style="padding: 20px; background: #f0f0f0; border-radius: 8px; margin: 20px 0;">
    <h3>Test Component Working!</h3>
    <p>Count: {{ count }}</p>
    <button @click="count++">Increment</button>
  </div>
</template>
