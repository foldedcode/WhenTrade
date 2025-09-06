<template>
  <select
    class="simple-select"
    :value="modelValue"
    :disabled="disabled"
    @change="handleChange"
  >
    <option
      v-for="option in options"
      :key="option.value"
      :value="option.value"
      :disabled="option.disabled"
    >
      {{ option.label }}
    </option>
  </select>
</template>

<script setup lang="ts">
export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

const props = defineProps<{
  modelValue: string | number
  options: SelectOption[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function handleChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<style scoped>
.simple-select {
  width: 100%;
  padding: var(--od-spacing-sm) var(--od-spacing-md);
  background: var(--od-background);
  color: var(--od-text-primary);
  border: 1px solid var(--od-border);
  border-radius: var(--od-radius-md);
  font-size: var(--od-font-md);
  cursor: pointer;
  transition: all 0.2s;
}

.simple-select:hover:not(:disabled) {
  border-color: var(--od-primary);
}

.simple-select:focus {
  outline: none;
  border-color: var(--od-primary);
  box-shadow: 0 0 0 3px var(--od-primary-alpha-20);
}

.simple-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>