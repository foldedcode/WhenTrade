<template>
  <div class="checkbox-field" :class="containerClasses">
    <div class="checkbox-wrapper">
      <div class="checkbox-container">
        <input
          :id="checkboxId"
          ref="inputRef"
          type="checkbox"
          :checked="checked"
          :disabled="disabled"
          :required="required"
          :value="value"
          :name="name"
          :aria-describedby="descriptionId"
          :aria-invalid="hasError"
          class="checkbox-input"
          @change="handleChange"
          @focus="handleFocus"
          @blur="handleBlur"
        />
        
        <div :class="checkboxClasses" @click="handleLabelClick">
          <!-- Check Icon -->
          <svg
            v-if="checked || indeterminate"
            class="checkbox-icon"
            :class="{ 'opacity-50': indeterminate }"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              v-if="!indeterminate"
              fill-rule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
            <path
              v-else
              fill-rule="evenodd"
              d="M4 10a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
      </div>
      
      <label v-if="label || $slots.default" :for="checkboxId" class="checkbox-label">
        <slot>
          {{ label }}
          <span v-if="required" class="text-destructive ml-1" aria-label="required">*</span>
        </slot>
      </label>
    </div>
    
    <!-- Helper Text / Error Message -->
    <div v-if="error || hint" :id="descriptionId" class="checkbox-description">
      <p v-if="error" class="text-destructive text-sm">
        {{ error }}
      </p>
      <p v-else-if="hint" class="text-muted-foreground text-sm">
        {{ hint }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { cn } from '../../composables/useDesignSystem'

export interface CheckboxProps {
  modelValue?: boolean | string[] | number[]
  checked?: boolean
  value?: string | number
  label?: string
  hint?: string
  error?: string
  disabled?: boolean
  required?: boolean
  size?: 'sm' | 'md' | 'lg'
  indeterminate?: boolean
  name?: string
}

export interface CheckboxEmits {
  'update:modelValue': [value: boolean | string[] | number[]]
  change: [checked: boolean, value?: string | number]
  focus: [event: FocusEvent]
  blur: [event: FocusEvent]
}

const props = withDefaults(defineProps<CheckboxProps>(), {
  disabled: false,
  required: false,
  size: 'md',
  indeterminate: false
})

const emit = defineEmits<CheckboxEmits>()

// Generate unique IDs
let idCounter = 0
const generateId = () => `checkbox-${++idCounter}`

// Refs
const inputRef = ref<HTMLInputElement>()
const checkboxId = generateId()
const descriptionId = generateId()

// Computed properties
const hasError = computed(() => !!props.error)

const checked = computed(() => {
  if (Array.isArray(props.modelValue) && props.value !== undefined) {
    return (props.modelValue as (string | number)[]).includes(props.value)
  }
  return props.checked !== undefined ? props.checked : !!props.modelValue
})

const containerClasses = computed(() => {
  const classes = ['space-y-2']
  if (props.disabled) classes.push('opacity-50')
  return cn(...classes)
})

const checkboxClasses = computed(() => {
  const classes = [
    'checkbox-box',
    `checkbox-box--${props.size}`
  ]
  
  if (checked.value || props.indeterminate) classes.push('checkbox-box--checked')
  if (hasError.value) classes.push('checkbox-box--error')
  if (props.disabled) classes.push('checkbox-box--disabled')
  
  return cn(...classes)
})

// Event handlers
const handleChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const isChecked = target.checked
  
  if (Array.isArray(props.modelValue) && props.value !== undefined) {
    const newValue = [...(props.modelValue as (string | number)[])]
    if (isChecked) {
      if (!newValue.includes(props.value)) {
        newValue.push(props.value)
      }
    } else {
      const index = newValue.indexOf(props.value)
      if (index > -1) {
        newValue.splice(index, 1)
      }
    }
    emit('update:modelValue', newValue as boolean | string[] | number[])
  } else {
    emit('update:modelValue', isChecked as boolean | string[] | number[])
  }
  
  emit('change', isChecked, props.value)
}

const handleFocus = (event: FocusEvent) => {
  emit('focus', event)
}

const handleBlur = (event: FocusEvent) => {
  emit('blur', event)
}

const handleLabelClick = () => {
  if (!props.disabled) {
    inputRef.value?.click()
  }
}

// Exposed methods
const focus = () => {
  inputRef.value?.focus()
}

const blur = () => {
  inputRef.value?.blur()
}

defineExpose({
  focus,
  blur,
  element: inputRef
})
</script>

<style scoped>
.checkbox-field {
  @apply w-full;
}

.checkbox-wrapper {
  @apply flex items-start space-x-3;
}

.checkbox-container {
  @apply relative flex-shrink-0;
}

.checkbox-input {
  @apply sr-only;
}

.checkbox-box {
  @apply relative flex items-center justify-center rounded border-2 border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900;
  @apply transition-all duration-200 ease-in-out;
  @apply focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-2;
  @apply hover:border-neutral-400 dark:hover:border-neutral-600;
  @apply cursor-pointer;
}

.checkbox-box--sm {
  @apply w-4 h-4;
}

.checkbox-box--md {
  @apply w-5 h-5;
}

.checkbox-box--lg {
  @apply w-6 h-6;
}

.checkbox-box--checked {
  @apply bg-primary-500 border-primary-500 text-white;
}

.checkbox-box--error {
  @apply border-error-500 focus-within:ring-error-500;
}

.checkbox-box--error.checkbox-box--checked {
  @apply bg-error-500 border-error-500;
}

.checkbox-box--disabled {
  @apply opacity-50 cursor-not-allowed;
}

.checkbox-icon {
  @apply w-3 h-3 text-current;
}

.checkbox-label {
  @apply text-sm font-medium text-neutral-900 dark:text-neutral-100 cursor-pointer;
  @apply select-none;
}

.checkbox-label:hover {
  @apply text-neutral-700 dark:text-neutral-300;
}

.checkbox-description {
  @apply mt-1 ml-8;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .checkbox-box {
    @apply border-2;
  }
  
  .checkbox-box--checked {
    @apply border-4;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .checkbox-box {
    @apply transition-none;
  }
}</style> 