/* When.Trade Design System Types */

/* ========================================
   颜色系统类型 - Color System Types
   ======================================== */

// 颜色变体级别
export type ColorShade = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950

// 颜色调色板类型
export interface ColorPalette {
  50: string
  100: string
  200: string
  300: string
  400: string
  500: string  // 主色调
  600: string
  700: string
  800: string
  900: string
  950?: string // 可选的最深色调
}

// 品牌色彩
export interface BrandColors {
  blue: ColorPalette
  green: ColorPalette
}

// 语义化颜色
export interface SemanticColors {
  primary: ColorPalette
  success: ColorPalette
  warning: ColorPalette
  error: ColorPalette
  neutral: ColorPalette
}

// 主题颜色映射
export interface ThemeColors {
  // 背景色
  bg: {
    primary: string
    secondary: string
    tertiary: string
    quaternary: string
    overlay: string
  }
  
  // 文本色
  text: {
    primary: string
    secondary: string
    tertiary: string
    quaternary: string
    inverse: string
  }
  
  // 边框色
  border: {
    primary: string
    secondary: string
    tertiary: string
    focus: string
    error: string
  }
  
  // 交互色
  interactive: {
    primary: string
    primaryHover: string
    primaryActive: string
    secondary: string
    secondaryHover: string
    secondaryActive: string
  }
}

/* ========================================
   字体系统类型 - Typography System Types
   ======================================== */

// 字体族
export type FontFamily = 'sans' | 'mono' | 'brand'

// 字体大小
export type FontSize = 
  | 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' 
  | '4xl' | '5xl' | '6xl' | '7xl' | '8xl' | '9xl'

// 字体权重
export type FontWeight = 
  | 'thin' | 'extralight' | 'light' | 'normal' | 'medium' 
  | 'semibold' | 'bold' | 'extrabold' | 'black'

// 行高
export type LineHeight = 
  | 'none' | 'tight' | 'snug' | 'normal' | 'relaxed' | 'loose'

// 字体配置
export interface TypographyConfig {
  fontFamily: Record<FontFamily, string[]>
  fontSize: Record<FontSize, [string, { lineHeight: string }]>
  fontWeight: Record<FontWeight, string>
  lineHeight: Record<LineHeight, string>
}

// 文本样式变体
export type TextVariant = 
  | 'display' | 'headline' | 'title' | 'body' | 'caption' | 'label'

/* ========================================
   间距系统类型 - Spacing System Types
   ======================================== */

// 间距尺度
export type SpacingScale = 
  | '0' | 'px' | '0.5' | '1' | '1.5' | '2' | '2.5' | '3' | '3.5' | '4' | '5' | '6' 
  | '7' | '8' | '9' | '10' | '11' | '12' | '14' | '16' | '18' | '20' | '24' | '28' 
  | '32' | '36' | '40' | '44' | '48' | '52' | '56' | '60' | '64' | '72' | '80' | '96'

// 语义化间距
export type SemanticSpacing = 
  | 'micro' | 'tiny' | 'small' | 'medium' | 'large' | 'huge' | 'massive'

// 组件间距
export type ComponentSpacing = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

/* ========================================
   尺寸系统类型 - Sizing System Types
   ======================================== */

// 圆角尺寸
export type BorderRadius = 
  | 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | 'full'

// 边框宽度
export type BorderWidth = '0' | '1' | '2' | '4' | '8'

// 阴影变体
export type BoxShadow = 
  | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'inner' | 'none'
  | 'blue' | 'green' | 'red'  // 品牌色阴影

/* ========================================
   动画系统类型 - Animation System Types
   ======================================== */

// 过渡时长
export type TransitionDuration = 
  | '75' | '100' | '150' | '200' | '300' | '500' | '700' | '1000'

// 缓动函数
export type TransitionTiming = 
  | 'linear' | 'in' | 'out' | 'in-out' | 'bounce'

// 动画变体
export type AnimationVariant = 
  | 'fade-in' | 'slide-in' | 'bounce-in' | 'pulse-slow' | 'spin-slow'

/* ========================================
   组件系统类型 - Component System Types
   ======================================== */

// 组件尺寸
export type ComponentSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

// 组件变体
export type ComponentVariant = 
  | 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success'

// 组件状态
export type ComponentState = 
  | 'idle' | 'hover' | 'active' | 'focus' | 'disabled' | 'loading'

// 按钮类型
export interface ButtonProps {
  variant?: ComponentVariant
  size?: ComponentSize
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
}

// 卡片类型
export interface CardProps {
  variant?: 'default' | 'outlined' | 'elevated' | 'interactive'
  padding?: ComponentSpacing
  hover?: boolean
}

// 徽章类型
export interface BadgeProps {
  variant?: ComponentVariant
  outline?: boolean
}

// 表单输入类型
export interface FormInputProps {
  size?: ComponentSize
  error?: boolean
  disabled?: boolean
}

/* ========================================
   布局系统类型 - Layout System Types
   ======================================== */

// 响应式断点
export type Breakpoint = 'sm' | 'md' | 'lg' | 'xl' | '2xl'

// 容器尺寸
export type ContainerSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl'

// 网格配置
export interface GridConfig {
  columns?: number
  gap?: SpacingScale | SemanticSpacing
  responsive?: boolean
}

// Flexbox配置
export interface FlexConfig {
  direction?: 'row' | 'col' | 'row-reverse' | 'col-reverse'
  wrap?: boolean
  justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'
  align?: 'start' | 'center' | 'end' | 'stretch'
  gap?: SpacingScale | SemanticSpacing
}

/* ========================================
   主题系统类型 - Theme System Types
   ======================================== */

// 主题模式
export type ThemeMode = 'light' | 'dark' | 'system'

// 主题配置
export interface ThemeConfig {
  mode: ThemeMode
  colors: ThemeColors
  typography: TypographyConfig
  spacing: Record<SpacingScale, string>
  borderRadius: Record<BorderRadius, string>
  boxShadow: Record<BoxShadow, string>
}

// 设计令牌
export interface DesignTokens {
  // 品牌标识
  brand: {
    name: string
    subtitle: string
    colors: BrandColors
  }
  
  // 颜色系统
  colors: {
    brand: BrandColors
    semantic: SemanticColors
    theme: ThemeColors
  }
  
  // 字体系统
  typography: TypographyConfig
  
  // 间距系统
  spacing: {
    scale: Record<SpacingScale, string>
    semantic: Record<SemanticSpacing, string>
    component: Record<ComponentSpacing, string>
  }
  
  // 尺寸系统
  sizing: {
    borderRadius: Record<BorderRadius, string>
    borderWidth: Record<BorderWidth, string>
    boxShadow: Record<BoxShadow, string>
  }
  
  // 动画系统
  animation: {
    duration: Record<TransitionDuration, string>
    timing: Record<TransitionTiming, string>
    variants: Record<AnimationVariant, string>
  }
  
  // 布局系统
  layout: {
    breakpoints: Record<Breakpoint, string>
    containers: Record<ContainerSize, string>
  }
  
  // Z-index层级
  zIndex: {
    dropdown: number
    sticky: number
    fixed: number
    modal: number
    popover: number
    tooltip: number
    toast: number
  }
}

/* ========================================
   设计系统配置类型 - Design System Config Types
   ======================================== */

// 设计系统配置
export interface DesignSystemConfig {
  tokens: DesignTokens
  theme: ThemeConfig
  components: {
    button: ButtonProps
    card: CardProps
    badge: BadgeProps
    input: FormInputProps
  }
}

// 设计系统上下文
export interface DesignSystemContext {
  config: DesignSystemConfig
  currentTheme: ThemeMode
  breakpoint: Breakpoint
  reducedMotion: boolean
  highContrast: boolean
}

/* ========================================
   工具类型 - Utility Types
   ======================================== */

// CSS属性值类型
export type CSSValue = string | number

// 响应式值类型
export type ResponsiveValue<T> = T | Partial<Record<Breakpoint, T>>

// 条件类型辅助
export type ConditionalClass<T extends string> = T | undefined | null | false

// 类名构建器类型
export type ClassNameBuilder = (...classes: ConditionalClass<string>[]) => string

// 样式对象类型
export type StyleObject = Record<string, CSSValue>

// 主题变量类型
export type ThemeVariable = `var(--${string})`

/* ========================================
   常量定义 - Constants
   ======================================== */

// 设计系统版本
export const DESIGN_SYSTEM_VERSION = '1.0.0'

// 默认主题模式
export const DEFAULT_THEME_MODE: ThemeMode = 'dark'

// 断点数值映射
export const BREAKPOINT_VALUES: Record<Breakpoint, number> = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

// 组件尺寸列表
export const COMPONENT_SIZES: ComponentSize[] = ['xs', 'sm', 'md', 'lg', 'xl']

// 组件变体列表
export const COMPONENT_VARIANTS: ComponentVariant[] = [
  'primary', 'secondary', 'outline', 'ghost', 'danger', 'success'
] 