<template>
  <div :class="cardClasses" @click="handleClick">
    <!-- Header -->
    <div v-if="$slots.header || title || $slots.actions" class="card-header">
      <div class="card-header-content">
        <slot name="header">
          <h3 v-if="title" class="card-title">
            {{ title }}
          </h3>
          <p v-if="subtitle" class="card-subtitle">
            {{ subtitle }}
          </p>
        </slot>
      </div>
      <div v-if="$slots.actions" class="card-actions">
        <slot name="actions" />
      </div>
    </div>
    
    <!-- Body -->
    <div :class="bodyClasses">
      <slot />
    </div>
    
    <!-- Footer -->
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '../../composables/useDesignSystem'

export interface CardProps {
  title?: string
  subtitle?: string
  variant?: 'default' | 'outline' | 'ghost' | 'filled'
  size?: 'sm' | 'md' | 'lg'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  interactive?: boolean
  disabled?: boolean
  loading?: boolean
}

export interface CardEmits {
  click: [event: MouseEvent]
}

const props = withDefaults(defineProps<CardProps>(), {
  variant: 'default',
  size: 'md',
  padding: 'md',
  hover: false,
  interactive: false,
  disabled: false,
  loading: false
})

const emit = defineEmits<CardEmits>()

const cardClasses = computed(() => {
  const classes = [
    'card',
    `card--${props.variant}`,
    `card--${props.size}`
  ]

  if (props.hover) classes.push('card--hover')
  if (props.interactive) classes.push('card--interactive')
  if (props.disabled) classes.push('card--disabled')
  if (props.loading) classes.push('card--loading')

  return cn(...classes)
})

const bodyClasses = computed(() => {
  const classes = ['card-body']
  
  if (props.padding !== 'none') {
    classes.push(`card-body--${props.padding}`)
  }

  return cn(...classes)
})

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading && props.interactive) {
    emit('click', event)
  }
}
</script>

<style scoped>
.card {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all var(--transition-normal);
  background: var(--color-bg-secondary);
  border-color: var(--color-border-primary);
}

/* Variants */
.card--default {
  border-color: var(--od-border);
}

.card--outline {
  border-width: 2px;
  border-color: var(--od-border);
  background: transparent;
}

.card--ghost {
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.card--filled {
  border-color: var(--od-border);
  background: var(--od-background-alt-alpha-50);
}

/* Sizes */
.card--sm {
  border-radius: var(--radius-sm);
}

.card--md {
  border-radius: var(--radius-md);
}

.card--lg {
  border-radius: var(--radius-lg);
}

/* States */
.card--hover:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-color: var(--color-border-secondary);
  transform: translateY(-1px);
}

.card--interactive {
  cursor: pointer;
}

.card--interactive:focus {
  outline: none;
}

.card--interactive:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 2px var(--od-background), 0 0 0 4px var(--od-primary);
}

.card--interactive:hover {
  box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
  border-color: var(--color-border-accent);
  background: var(--color-bg-elevated);
  transform: translateY(-2px);
}

.card--interactive:active {
  transform: scale(0.98);
}

.card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card--loading {
  cursor: wait;
}

.card--loading::after {
  position: absolute;
  inset: 0;
  background: var(--od-background-alpha-50);
  backdrop-filter: blur(4px);
  border-radius: var(--radius-lg);
  content: '';
}

/* Header */
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.5rem;
  padding-bottom: 0;
}

.card-header-content {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.025em;
  margin-bottom: 0.25rem;
}

.card-subtitle {
  font-size: 0.875rem;
  color: var(--od-text-secondary);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 1rem;
}

/* Body */
.card-body {
  width: 100%;
}

.card-body--sm {
  padding: 1rem;
}

.card-body--md {
  padding: 1.5rem;
}

.card-body--lg {
  padding: 2rem;
}

/* Footer */
.card-footer {
  display: flex;
  align-items: center;
  padding: 1.5rem;
  padding-top: 0;
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .card--default,
  .card--outline {
    border-width: 2px;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .card {
    transition: none;
  }
  
  .card--interactive:active {
    transform: scale(1);
  }
}</style> 