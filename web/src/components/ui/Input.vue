<template>
  <div class="input-field" :class="containerClasses">
    <!-- Label -->
    <label v-if="label" :for="inputId" class="input-label">
      {{ label }}
      <span v-if="required" class="text-destructive ml-1" aria-label="required">*</span>
    </label>
    
    <!-- Input Container -->
    <div class="input-container">
      <!-- Prefix -->
      <div v-if="$slots.prefix || prefixIcon" class="input-prefix">
        <slot name="prefix">
          <component v-if="prefixIcon" :is="prefixIcon" class="w-4 h-4 text-muted-foreground" />
        </slot>
      </div>
      
      <!-- Input Element -->
      <input
        :id="inputId"
        ref="inputRef"
        :name="name"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :autocomplete="autocomplete"
        :aria-label="ariaLabel || label"
        :aria-describedby="descriptionId"
        :aria-invalid="hasError"
        :class="inputClasses"
        @input="handleInput"
        @blur="handleBlur"
        @focus="handleFocus"
        @keydown="handleKeydown"
      />
      
      <!-- Suffix -->
      <div v-if="$slots.suffix || suffixIcon || showClearButton || showPasswordToggle" class="input-suffix">
        <!-- Clear Button -->
        <button
          v-if="showClearButton && modelValue && !readonly"
          type="button"
          class="input-action-btn"
          :aria-label="$t?.('common.clear') || 'Clear'"
          @click="handleClear"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        
        <!-- Password Toggle -->
        <button
          v-if="showPasswordToggle"
          type="button"
          class="input-action-btn"
          :aria-label="showPassword ? ($t?.('common.hidePassword') || 'Hide password') : ($t?.('common.showPassword') || 'Show password')"
          @click="togglePassword"
        >
          <svg v-if="showPassword" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L12 12m-2.122-2.122L12 12m6.878-6.878L12 12m0 0l3-3M12 12l3-3" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.543 7-1.275 4.057-5.065 7-9.543 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </button>
        
        <!-- Custom Suffix -->
        <slot name="suffix">
          <component v-if="suffixIcon" :is="suffixIcon" class="w-4 h-4 text-muted-foreground" />
        </slot>
      </div>
    </div>
    
    <!-- Helper Text / Error Message -->
    <div v-if="error || hint" :id="descriptionId" class="input-description">
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

// Generate unique IDs
let idCounter = 0
const generateId = () => `input-${++idCounter}`

export interface InputProps {
  modelValue?: string | number
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search'
  name?: string
  label?: string
  placeholder?: string
  hint?: string
  error?: string
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  size?: 'sm' | 'md' | 'lg'
  prefixIcon?: string
  suffixIcon?: string
  clearable?: boolean
  autocomplete?: string
  ariaLabel?: string
}

export interface InputEmits {
  'update:modelValue': [value: string | number]
  blur: [event: FocusEvent]
  focus: [event: FocusEvent]
  keydown: [event: KeyboardEvent]
  clear: []
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
  disabled: false,
  readonly: false,
  required: false,
  size: 'md',
  clearable: false
})

const emit = defineEmits<InputEmits>()

const inputRef = ref<HTMLInputElement>()
const inputId = generateId()
const descriptionId = generateId()
const showPassword = ref(false)

// Computed properties
const hasError = computed(() => !!props.error)
const showClearButton = computed(() => props.clearable && !props.disabled)
const showPasswordToggle = computed(() => props.type === 'password')
const inputType = computed(() => {
  if (props.type === 'password') {
    return showPassword.value ? 'text' : 'password'
  }
  return props.type
})

const containerClasses = computed(() => {
  const classes = ['space-y-2']
  if (props.disabled) classes.push('opacity-50')
  return cn(...classes)
})

const inputClasses = computed(() => {
  const classes = [
    'input-base',
    `input--${props.size}`
  ]
  
  if (hasError.value) classes.push('input--error')
  if (props.disabled) classes.push('input--disabled')
  if (props.readonly) classes.push('input--readonly')
  if (props.prefixIcon) classes.push('input--with-prefix')
  if (props.suffixIcon || showClearButton.value || showPasswordToggle.value) classes.push('input--with-suffix')
  
  return cn(...classes)
})

// Event handlers
const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const value = props.type === 'number' ? Number(target.value) : target.value
  emit('update:modelValue', value)
}

const handleBlur = (event: FocusEvent) => {
  emit('blur', event)
}

const handleFocus = (event: FocusEvent) => {
  emit('focus', event)
}

const handleKeydown = (event: KeyboardEvent) => {
  emit('keydown', event)
}

const handleClear = () => {
  emit('update:modelValue', '')
  emit('clear')
  setTimeout(() => {
    inputRef.value?.focus()
  }, 0)
}

const togglePassword = () => {
  showPassword.value = !showPassword.value
  setTimeout(() => {
    inputRef.value?.focus()
  }, 0)
}

// Exposed methods
const focus = () => {
  inputRef.value?.focus()
}

const blur = () => {
  inputRef.value?.blur()
}

const select = () => {
  inputRef.value?.select()
}

defineExpose({
  focus,
  blur,
  select,
  element: inputRef
})
</script>

<style scoped>
.input-field {
  width: 100%;
}

.input-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--od-text-primary);
}

.input-container {
  position: relative;
  display: flex;
  align-items: center;
}

.input-prefix,
.input-suffix {
  position: absolute;
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  pointer-events: none;
}

.input-prefix {
  left: 0.75rem;
}

.input-suffix {
  right: 0.75rem;
}

.input-action-btn {
  pointer-events: auto;
  color: var(--od-text-muted);
  transition: color 200ms;
  padding: 0.25rem;
  border-radius: var(--radius-sm);
}

.input-action-btn:hover {
  color: var(--od-text-primary);
}

.input-action-btn:focus {
  outline: none;
}

.input-action-btn:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 2px var(--od-background), 0 0 0 4px var(--od-primary);
}

.input-base {
  display: flex;
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--od-border);
  background: var(--od-background);
  color: var(--od-text-primary);
  transition: all 200ms;
}

.input-base::placeholder {
  color: var(--od-text-muted);
}

.input-base:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 2px var(--od-background), 0 0 0 4px var(--od-primary);
}

.input-base:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.input-base:read-only {
  cursor: default;
  background: var(--od-background-alt);
}

.input-base::-webkit-file-upload-button {
  border: 0;
  background: transparent;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Sizes */
.input--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  min-height: var(--size-8);
}

.input--md {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  min-height: var(--size-10);
}

.input--lg {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  min-height: var(--size-12);
}

/* States */
.input--error {
  border-color: var(--od-error);
}

.input--error:focus-visible {
  box-shadow: 0 0 0 2px var(--od-background), 0 0 0 4px var(--od-error);
}

.input--with-prefix {
  padding-left: 2.5rem;
}

.input--with-suffix {
  padding-right: 2.5rem;
}

.input--with-prefix.input--with-suffix {
  padding-left: 2.5rem;
  padding-right: 2.5rem;
}

.input-description {
  margin-top: 0.25rem;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .input-base {
    border-width: 2px;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .input-base,
  .input-action-btn {
    transition: none;
  }
}</style> 