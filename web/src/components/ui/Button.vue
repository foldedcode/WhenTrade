<template>
  <button
    ref="buttonRef"
    :class="buttonClasses"
    :disabled="disabled || loading"
    :type="type"
    :aria-label="ariaLabel"
    :aria-describedby="ariaDescribedby"
    :aria-pressed="pressed"
    @click="handleClick"
    @keydown="handleKeydown"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
    @mousedown="handleMouseDown"
    @mouseup="handleMouseUp"
  >
    <!-- 背景光效 -->
    <div v-if="variant === 'primary'" class="button__glow" :class="{ 'button__glow--active': isActive }"></div>
    
    <!-- 涟漪效果容器 -->
    <div ref="rippleContainer" class="button__ripple-container">
      <div
        v-for="ripple in ripples"
        :key="ripple.id"
        class="button__ripple"
        :style="ripple.style"
      ></div>
    </div>

    <!-- Loading State -->
    <Transition name="fade" mode="out-in">
      <div v-if="loading" class="button__loading">
        <div class="button__spinner" :class="getSpinnerSize()">
          <div class="button__spinner-circle"></div>
        </div>
        <span v-if="loadingText" class="button__loading-text">{{ loadingText }}</span>
      </div>
      
      <div v-else class="button__content">
        <!-- Icon (Left) -->
        <Transition name="slide-right" mode="out-in">
          <span v-if="icon && iconPosition === 'left'" class="button__icon button__icon--left">
            <component :is="iconComponent" :class="getIconSize()" />
          </span>
        </Transition>
        
        <!-- Content -->
        <span class="button__text">
          <slot />
        </span>
        
        <!-- Icon (Right) -->
        <Transition name="slide-left" mode="out-in">
          <span v-if="icon && iconPosition === 'right'" class="button__icon button__icon--right">
            <component :is="iconComponent" :class="getIconSize()" />
          </span>
        </Transition>
        
        <!-- Badge -->
        <Transition name="scale" mode="out-in">
          <span v-if="badge" class="button__badge" :class="getBadgeVariant()">
            {{ badge }}
          </span>
        </Transition>
      </div>
    </Transition>
  </button>
</template>

<script setup lang="ts">
import { computed, ref, nextTick } from 'vue'

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'warning'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  disabled?: boolean
  loading?: boolean
  loadingText?: string
  icon?: string
  iconPosition?: 'left' | 'right'
  fullWidth?: boolean
  type?: 'button' | 'submit' | 'reset'
  pressed?: boolean
  ariaLabel?: string
  ariaDescribedby?: string
  badge?: string | number
  badgeVariant?: 'default' | 'success' | 'warning' | 'error'
  ripple?: boolean
  glow?: boolean
}

export interface ButtonEmits {
  click: [event: MouseEvent]
  keydown: [event: KeyboardEvent]
  mouseenter: [event: MouseEvent]
  mouseleave: [event: MouseEvent]
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  iconPosition: 'left',
  fullWidth: false,
  type: 'button',
  pressed: undefined,
  badgeVariant: 'default',
  ripple: true,
  glow: false
})

const emit = defineEmits<ButtonEmits>()

// Refs
const buttonRef = ref<HTMLButtonElement>()
const rippleContainer = ref<HTMLDivElement>()

// State
const isHovered = ref(false)
const isActive = ref(false)
const ripples = ref<Array<{
  id: number
  style: Record<string, string>
}>>([])

let rippleId = 0

// Icon component resolution
const iconComponent = computed(() => {
  return props.icon ? `Icon${props.icon}` : null
})

// Computed classes
const buttonClasses = computed(() => {
  const classes = [
    'button',
    `button--${props.variant}`,
    `button--${props.size}`
  ]

  if (props.fullWidth) classes.push('button--full-width')
  if (props.loading) classes.push('button--loading')
  if (props.disabled) classes.push('button--disabled')
  if (props.pressed) classes.push('button--pressed')
  if (isHovered.value) classes.push('button--hovered')
  if (isActive.value) classes.push('button--active')
  if (props.glow) classes.push('button--glow-enabled')

  return classes.join(' ')
})

// Size utilities
const getIconSize = () => {
  const sizes = {
    xs: 'w-3 h-3',
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
    xl: 'w-6 h-6'
  }
  return sizes[props.size]
}

const getSpinnerSize = () => {
  const sizes = {
    xs: 'button__spinner--xs',
    sm: 'button__spinner--sm',
    md: 'button__spinner--md',
    lg: 'button__spinner--lg',
    xl: 'button__spinner--xl'
  }
  return sizes[props.size]
}

const getBadgeVariant = () => {
  return `button__badge--${props.badgeVariant}`
}

// Event handlers
const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    if (props.ripple) {
      createRipple(event)
    }
    emit('click', event)
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (!props.disabled && !props.loading) {
      buttonRef.value?.click()
    }
  }
  emit('keydown', event)
}

const handleMouseEnter = (event: MouseEvent) => {
  isHovered.value = true
  emit('mouseenter', event)
}

const handleMouseLeave = (event: MouseEvent) => {
  isHovered.value = false
  isActive.value = false
  emit('mouseleave', event)
}

const handleMouseDown = () => {
  isActive.value = true
}

const handleMouseUp = () => {
  isActive.value = false
}

// Ripple effect
const createRipple = async (event: MouseEvent) => {
  if (!rippleContainer.value) return

  const rect = rippleContainer.value.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height)
  const x = event.clientX - rect.left - size / 2
  const y = event.clientY - rect.top - size / 2

  const ripple = {
    id: rippleId++,
    style: {
      left: `${x}px`,
      top: `${y}px`,
      width: `${size}px`,
      height: `${size}px`
    }
  }

  ripples.value.push(ripple)

  // Remove ripple after animation
  setTimeout(() => {
    const index = ripples.value.findIndex(r => r.id === ripple.id)
    if (index > -1) {
      ripples.value.splice(index, 1)
    }
  }, 600)
}

// Exposed methods
const focus = () => {
  buttonRef.value?.focus()
}

const blur = () => {
  buttonRef.value?.blur()
}

defineExpose({
  focus,
  blur,
  element: buttonRef
})
</script>

<style scoped>
.button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  overflow: hidden;
  user-select: none;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.button:focus {
  outline: none;
}

.button:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 2px;
  --tw-ring-offset-shadow: 0 0 0 2px var(--tw-ring-offset-color);
  --tw-ring-shadow: 0 0 0 calc(2px + 2px) var(--tw-ring-color);
  box-shadow: var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow, 0 0 #0000);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* One Dark Pro 主题适配 */
[data-theme="onedark"] .button:focus-visible {
  --tw-ring-offset-color: var(--od-background);
  --tw-ring-color: var(--od-primary);
}

/* 背景光效 */
.button__glow {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  background: radial-gradient(circle at center, var(--brand-blue-400) 0%, transparent 70%);
  transition: opacity var(--transition-normal);
}

[data-theme="onedark"] .button__glow {
  background: radial-gradient(circle at center, var(--onedark-accent-blue) 0%, transparent 70%);
}

.button--glow-enabled .button__glow {
  opacity: 0.2;
}

.button--glow-enabled:hover .button__glow,
.button__glow--active {
  opacity: 0.4;
}

/* 涟漪效果容器 */
.button__ripple-container {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  border-radius: inherit;
}

.button__ripple {
  position: absolute;
  border-radius: 9999px;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.3);
  transform: scale(0);
  animation: ripple 0.6s ease-out;
}

[data-theme="onedark"] .button__ripple {
  background: rgba(171, 178, 191, 0.3);
}

@keyframes ripple {
  to {
    transform: scale(2);
    opacity: 0;
  }
}

/* 内容布局 */
.button__content {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 10;
}

.button__text {
  transition: all 200ms;
}

.button__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 200ms;
}

.button__icon--left {
  margin-right: 0.5rem;
}

.button__icon--right {
  margin-left: 0.5rem;
}

/* Loading 状态 */
.button__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 10;
}

.button__spinner {
  position: relative;
}

.button__spinner-circle {
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 9999px;
  animation: spin 1s linear infinite;
}

.button__spinner--xs .button__spinner-circle {
  width: 0.75rem;
  height: 0.75rem;
}

.button__spinner--sm .button__spinner-circle {
  width: 0.875rem;
  height: 0.875rem;
}

.button__spinner--md .button__spinner-circle {
  width: 1rem;
  height: 1rem;
}

.button__spinner--lg .button__spinner-circle {
  width: 1.25rem;
  height: 1.25rem;
}

.button__spinner--xl .button__spinner-circle {
  width: 1.5rem;
  height: 1.5rem;
}

.button__loading-text {
  margin-left: 0.5rem;
  font-size: 0.875rem;
}

/* Badge */
.button__badge {
  position: absolute;
  top: -0.25rem;
  right: -0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.25rem;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 9999px;
  transform: translateZ(0);
  transition: all 200ms;
  box-shadow: 0 0 0 2px var(--color-bg-primary);
}

[data-theme="onedark"] .button__badge {
  box-shadow: 0 0 0 2px var(--onedark-bg-primary);
}

.button__badge--default {
  background: rgb(71 85 105);
  color: rgb(226 232 240);
}

[data-theme="onedark"] .button__badge--default {
  background: var(--od-text-muted);
  color: var(--od-text-primary);
}

.button__badge--success {
  background: rgb(34 197 94);
  color: white;
}

[data-theme="onedark"] .button__badge--success {
  background: var(--od-success);
  color: var(--od-text-primary);
}

.button__badge--warning {
  background: rgb(234 179 8);
  color: white;
}

[data-theme="onedark"] .button__badge--warning {
  background: var(--od-warning);
  color: var(--od-background);
}

.button__badge--error {
  background: rgb(239 68 68);
  color: white;
}

[data-theme="onedark"] .button__badge--error {
  background: var(--od-error);
  color: var(--od-text-primary);
}

/* Variants */
.button--primary {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--shadow-blue);
  position: relative;
  overflow: hidden;
}

[data-theme="onedark"] .button--primary {
  background: var(--onedark-gradient-primary);
  color: var(--od-text-primary);
  box-shadow: var(--onedark-shadow-blue);
}

.button--primary:hover:not(:disabled):not(.button--loading) {
  background: var(--gradient-primary-hover);
  box-shadow: var(--shadow-dark-lg), var(--shadow-blue);
  transform: translateY(-1px) scale(1.02);
}

[data-theme="onedark"] .button--primary:hover:not(:disabled):not(.button--loading) {
  background: var(--onedark-gradient-primary-hover);
  box-shadow: var(--onedark-shadow-dark-lg), var(--onedark-shadow-blue);
}

.button--primary:active:not(:disabled):not(.button--loading) {
  transform: translateY(0);
  box-shadow: var(--shadow-dark-sm), var(--shadow-blue);
}

[data-theme="onedark"] .button--primary:active:not(:disabled):not(.button--loading) {
  box-shadow: var(--onedark-shadow-dark-sm), var(--onedark-shadow-blue);
}

.button--secondary {
  background: rgb(51 65 85);
  color: rgb(226 232 240);
  border: 1px solid rgb(71 85 105);
  box-shadow: var(--shadow-dark-xs);
}

[data-theme="onedark"] .button--secondary {
  background: var(--od-background-alt);
  color: var(--od-text-secondary);
  border: 1px solid var(--od-border);
  box-shadow: var(--onedark-shadow-dark-xs);
}

.button--secondary:hover:not(:disabled):not(.button--loading) {
  background: rgb(71 85 105);
  border-color: rgb(100 116 139);
  color: white;
  box-shadow: var(--shadow-dark-sm);
  transform: translateY(-1px);
}

[data-theme="onedark"] .button--secondary:hover:not(:disabled):not(.button--loading) {
  background: var(--od-background-light);
  border-color: var(--od-border-light);
  color: var(--od-text-primary);
  box-shadow: var(--onedark-shadow-dark-sm);
}

.button--outline {
  background: transparent;
  color: rgb(203 213 225);
  border: 1px solid rgb(71 85 105);
}

[data-theme="onedark"] .button--outline {
  background: transparent;
  color: var(--od-text-secondary);
  border: 1px solid var(--od-border);
}

.button--outline:hover:not(:disabled):not(.button--loading) {
  background: rgb(51 65 85);
  color: white;
  border-color: rgb(100 116 139);
}

[data-theme="onedark"] .button--outline:hover:not(:disabled):not(.button--loading) {
  background: var(--od-background-alt);
  color: var(--od-text-primary);
  border-color: var(--od-border-light);
}

.button--ghost {
  background: transparent;
  color: rgb(203 213 225);
}

[data-theme="onedark"] .button--ghost {
  background: transparent;
  color: var(--od-text-secondary);
}

.button--ghost:hover:not(:disabled):not(.button--loading) {
  background: rgba(51, 65, 85, 0.5);
  color: white;
}

[data-theme="onedark"] .button--ghost:hover:not(:disabled):not(.button--loading) {
  background: var(--od-background-alt-alpha-50);
  color: var(--od-text-primary);
}

.button--danger {
  background: var(--gradient-error);
  color: white;
  box-shadow: var(--shadow-red);
}

[data-theme="onedark"] .button--danger {
  background: var(--onedark-gradient-error);
  color: var(--od-text-primary);
  box-shadow: var(--onedark-shadow-red);
}

.button--danger:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--shadow-dark-lg), var(--shadow-red);
  transform: translateY(-1px);
}

[data-theme="onedark"] .button--danger:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--onedark-shadow-dark-lg), var(--onedark-shadow-red);
}

.button--success {
  background: var(--gradient-success);
  color: white;
  box-shadow: var(--shadow-green);
}

[data-theme="onedark"] .button--success {
  background: var(--onedark-gradient-success);
  color: var(--od-text-primary);
  box-shadow: var(--onedark-shadow-green);
}

.button--success:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--shadow-dark-lg), var(--shadow-green);
  transform: translateY(-1px);
}

[data-theme="onedark"] .button--success:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--onedark-shadow-dark-lg), var(--onedark-shadow-green);
}

.button--warning {
  background: var(--gradient-warning);
  color: white;
  box-shadow: var(--shadow-yellow);
}

[data-theme="onedark"] .button--warning {
  background: var(--onedark-gradient-warning);
  color: var(--od-background);
  box-shadow: var(--onedark-shadow-yellow);
}

.button--warning:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--shadow-dark-lg), var(--shadow-yellow);
  transform: translateY(-1px);
}

[data-theme="onedark"] .button--warning:hover:not(:disabled):not(.button--loading) {
  box-shadow: var(--onedark-shadow-dark-lg), var(--onedark-shadow-yellow);
}

/* Sizes */
.button--xs {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  min-height: var(--space-6);
}

.button--sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  min-height: var(--space-8);
}

.button--md {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  min-height: var(--space-10);
}

.button--lg {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  min-height: var(--space-12);
}

.button--xl {
  padding: 1rem 2rem;
  font-size: 1.125rem;
  min-height: var(--space-14);
}

/* States */
.button--full-width {
  width: 100%;
}

.button--pressed {
  transform: scale(0.98);
}

.button--disabled {
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.button--loading {
  cursor: wait;
}

/* Animations */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: all var(--transition-fast);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(-4px);
}

.slide-right-leave-to {
  opacity: 0;
  transform: translateX(4px);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all var(--transition-fast);
}

.slide-left-enter-from {
  opacity: 0;
  transform: translateX(4px);
}

.slide-left-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}

.scale-enter-active,
.scale-leave-active {
  transition: all var(--transition-fast);
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

/* 高对比度支持 */
@media (prefers-contrast: high) {
  .button {
    border-width: 2px;
  }
}

/* 减少动画支持 */
@media (prefers-reduced-motion: reduce) {
  .button,
  .button__glow,
  .button__text,
  .button__icon,
  .button__badge {
    transition: none;
  }
  
  .button__ripple {
    display: none;
  }
  
  .button:hover:not(:disabled):not(.button--loading) {
    transform: none;
  }
}
</style>