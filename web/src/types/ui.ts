// Base UI component sizes
export type UISize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

// Component variants
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success'
export type CardVariant = 'default' | 'outline' | 'ghost' | 'filled'
export type InputType = 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search'

// Common props shared across components
export interface BaseComponentProps {
  disabled?: boolean
  loading?: boolean
  size?: UISize
}

export interface FormFieldProps extends BaseComponentProps {
  label?: string
  hint?: string
  error?: string
  required?: boolean
}

// Select option interface
export interface SelectOption {
  value: any
  label: string
  disabled?: boolean
  group?: string
  [key: string]: any
}

// Theme and design system types
export type ThemeMode = 'light' | 'dark' | 'system'

export interface DesignTokens {
  colors: Record<string, string>
  spacing: Record<string, string>
  typography: Record<string, string>
  shadows: Record<string, string>
  radius: Record<string, string>
  breakpoints: Record<string, string>
}

// Animation and transition types
export type TransitionName = 'fade' | 'slide' | 'scale' | 'slide-up' | 'slide-down'
export type TransitionMode = 'in-out' | 'out-in' | 'default'

export interface TransitionConfig {
  name: TransitionName
  mode?: TransitionMode
  duration?: number | { enter: number; leave: number }
  delay?: number
}

// Layout and positioning
export type Position = 'top' | 'bottom' | 'left' | 'right' | 'center'
export type Alignment = 'start' | 'center' | 'end'
export type Direction = 'horizontal' | 'vertical'

// Toast and notification types
export type ToastType = 'success' | 'error' | 'warning' | 'info'
export type ToastPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'bottom-center'

export interface ToastAction {
  label: string
  action: () => void
  style?: 'primary' | 'secondary'
}

export interface ToastOptions {
  id?: string
  title: string
  message?: string
  type: ToastType
  duration?: number
  position?: ToastPosition
  persistent?: boolean
  actions?: ToastAction[]
}

// Loading states
export type LoadingType = 'spinner' | 'dots' | 'pulse' | 'bars' | 'skeleton'

export interface LoadingState {
  loading: boolean
  progress?: number
  message?: string
  description?: string
}

// Modal and dialog types
export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'
export type ModalPlacement = 'center' | 'top' | 'bottom'

export interface ModalOptions {
  size?: ModalSize
  placement?: ModalPlacement
  closable?: boolean
  maskClosable?: boolean
  keyboard?: boolean
  centered?: boolean
}

// Form validation
export interface ValidationRule {
  required?: boolean
  min?: number
  max?: number
  pattern?: RegExp
  validator?: (value: any) => boolean | string
  message?: string
}

export interface FormFieldState {
  value: any
  error?: string
  touched: boolean
  valid: boolean
}

// Accessibility
export interface A11yProps {
  ariaLabel?: string
  ariaDescribedby?: string
  ariaLabelledby?: string
  role?: string
  tabIndex?: number
}

// Event handlers
export interface ComponentEvents {
  onClick?: (event: MouseEvent) => void
  onFocus?: (event: FocusEvent) => void
  onBlur?: (event: FocusEvent) => void
  onKeydown?: (event: KeyboardEvent) => void
  onChange?: (value: any) => void
}

// Responsive breakpoint system
export interface ResponsiveValue<T> {
  xs?: T
  sm?: T
  md?: T
  lg?: T
  xl?: T
}

// CSS class utilities
export type ConditionalClasses = Record<string, boolean>
export type ClassValue = string | ConditionalClasses | (string | ConditionalClasses)[]

// Component instance references
export interface ComponentRef {
  focus: () => void
  blur: () => void
  element: HTMLElement | null
}

// Color system
export type ColorName = 
  | 'primary' 
  | 'secondary' 
  | 'accent' 
  | 'neutral' 
  | 'success' 
  | 'warning' 
  | 'error' 
  | 'info'

export type ColorShade = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900

// Typography
export type FontWeight = 'light' | 'normal' | 'medium' | 'semibold' | 'bold'
export type FontSize = 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl'

// Layout components
export interface GridProps {
  cols?: number | ResponsiveValue<number>
  gap?: UISize | ResponsiveValue<UISize>
  rows?: number | ResponsiveValue<number>
}

export interface FlexProps {
  direction?: Direction | ResponsiveValue<Direction>
  wrap?: boolean | ResponsiveValue<boolean>
  justify?: Alignment | ResponsiveValue<Alignment>
  align?: Alignment | ResponsiveValue<Alignment>
  gap?: UISize | ResponsiveValue<UISize>
} 