/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // 品牌色彩系统
      colors: {
        // When.Trade 品牌色
        'brand': {
          // 专业金融终端金色系（主要）
          gold: {
            50: '#fefbf3',
            100: '#fef3c7',
            200: '#fde68a',
            300: '#fcd34d',
            400: '#fbbf24',
            500: '#d4af37',  // 主品牌色 - 专业金色
            600: '#b8941f',
            700: '#92400e',
            800: '#78350f',
            900: '#451a03',
            950: '#1c0a00',
          },
          // 标准蓝色系（备选）
          blue: {
            50: '#eff6ff',
            100: '#dbeafe',
            200: '#bfdbfe',
            300: '#93c5fd',
            400: '#60a5fa',
            500: '#3b82f6',  // 标准品牌色
            600: '#2563eb',
            700: '#1d4ed8',
            800: '#1e40af',
            900: '#1e3a8a',
            950: '#172554',
          },
          green: {
            50: '#ecfdf5',
            100: '#d1fae5',
            200: '#a7f3d0',
            300: '#6ee7b7',
            400: '#34d399',
            500: '#10b981',  // 成功色
            600: '#059669',
            700: '#047857',
            800: '#065f46',
            900: '#064e3b',
          }
        },
        
        // 中性色系 - 基于项目现有深色主题
        neutral: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',  // 深色背景
          900: '#0f172a',  // 主背景
          950: '#020617',
        },

        // 语义化颜色映射 - 主题感知的动态颜色
        primary: {
          50: '#fefbf3',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#d4af37',  // 专业金色作为默认主色
          600: '#b8941f',
          700: '#92400e',
          800: '#78350f',
          900: '#451a03',
          DEFAULT: 'var(--theme-primary)',  // 主题感知的主色
        },
        
        success: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },

        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },

        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },

        // 兼容现有的When.Trade颜色
        'when-gold': '#d4af37',    // 新的主色 - 专业金色
        'when-blue': '#3b82f6',    // 保留蓝色用于标准模式
        'when-green': '#10b981',
        'when-dark': '#1e293b',
      },

      // 字体系统
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        'mono': ['Proto Mono', 'monospace'],
        'brand': ['Inter', 'ui-sans-serif', 'system-ui'],
      },

      // 字体大小 - 扩展Tailwind默认值
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1.25' }],      // 12px
        'sm': ['0.875rem', { lineHeight: '1.375' }],    // 14px
        'base': ['1rem', { lineHeight: '1.5' }],        // 16px
        'lg': ['1.125rem', { lineHeight: '1.5' }],      // 18px
        'xl': ['1.25rem', { lineHeight: '1.5' }],       // 20px
        '2xl': ['1.5rem', { lineHeight: '1.375' }],     // 24px
        '3xl': ['1.875rem', { lineHeight: '1.25' }],    // 30px
        '4xl': ['2.25rem', { lineHeight: '1.25' }],     // 36px
        '5xl': ['3rem', { lineHeight: '1.125' }],       // 48px
        '6xl': ['3.75rem', { lineHeight: '1' }],        // 60px
        '7xl': ['4.5rem', { lineHeight: '1' }],         // 72px
        '8xl': ['6rem', { lineHeight: '1' }],           // 96px
        '9xl': ['8rem', { lineHeight: '1' }],           // 128px
      },

      // 字体权重
      fontWeight: {
        'thin': '100',
        'extralight': '200',
        'light': '300',
        'normal': '400',
        'medium': '500',
        'semibold': '600',
        'bold': '700',
        'extrabold': '800',
        'black': '900',
      },

      // 间距系统 - 基于8pt网格
      spacing: {
        '0': '0',
        'px': '1px',
        '0.5': '0.125rem',   // 2px
        '1': '0.25rem',      // 4px
        '1.5': '0.375rem',   // 6px
        '2': '0.5rem',       // 8px
        '2.5': '0.625rem',   // 10px
        '3': '0.75rem',      // 12px
        '3.5': '0.875rem',   // 14px
        '4': '1rem',         // 16px
        '5': '1.25rem',      // 20px
        '6': '1.5rem',       // 24px
        '7': '1.75rem',      // 28px
        '8': '2rem',         // 32px
        '9': '2.25rem',      // 36px
        '10': '2.5rem',      // 40px
        '11': '2.75rem',     // 44px
        '12': '3rem',        // 48px
        '14': '3.5rem',      // 56px
        '16': '4rem',        // 64px
        '18': '4.5rem',      // 72px
        '20': '5rem',        // 80px
        '24': '6rem',        // 96px
        '28': '7rem',        // 112px
        '32': '8rem',        // 128px
        '36': '9rem',        // 144px
        '40': '10rem',       // 160px
        '44': '11rem',       // 176px
        '48': '12rem',       // 192px
        '52': '13rem',       // 208px
        '56': '14rem',       // 224px
        '60': '15rem',       // 240px
        '64': '16rem',       // 256px
        '72': '18rem',       // 288px
        '80': '20rem',       // 320px
        '96': '24rem',       // 384px
      },

      // 圆角系统
      borderRadius: {
        'none': '0',
        'sm': '0.125rem',    // 2px
        'DEFAULT': '0.25rem', // 4px
        'md': '0.375rem',    // 6px
        'lg': '0.5rem',      // 8px
        'xl': '0.75rem',     // 12px
        '2xl': '1rem',       // 16px
        '3xl': '1.5rem',     // 24px
        'full': '9999px',
      },

      // 阴影系统
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'DEFAULT': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        'inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
        'none': '0 0 #0000',
        
        // 品牌色阴影
        'blue': '0 4px 14px 0 rgba(59, 130, 246, 0.15)',
        'green': '0 4px 14px 0 rgba(16, 185, 129, 0.15)', 
        'red': '0 4px 14px 0 rgba(239, 68, 68, 0.15)',
      },

      // 动画时长
      transitionDuration: {
        '75': '75ms',
        '100': '100ms',
        '150': '150ms',
        '200': '200ms',
        '300': '300ms',
        '500': '500ms',
        '700': '700ms',
        '1000': '1000ms',
      },

      // 缓动函数
      transitionTimingFunction: {
        'linear': 'linear',
        'in': 'cubic-bezier(0.4, 0, 1, 1)',
        'out': 'cubic-bezier(0, 0, 0.2, 1)',
        'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'bounce': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },

      // Z-index层级
      zIndex: {
        '0': '0',
        '10': '10',
        '20': '20',
        '30': '30',
        '40': '40',
        '50': '50',
        'auto': 'auto',
        'dropdown': '1000',
        'sticky': '1020',
        'fixed': '1030',
        'modal': '1040',
        'popover': '1050',
        'tooltip': '1060',
        'toast': '1070',
      },

      // 断点系统（已内置但重新定义以保持一致性）
      screens: {
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },

      // 动画关键帧
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'bounce-in': {
          '0%': { opacity: '0', transform: 'scale(0.3)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'spin-slow': {
          'to': { transform: 'rotate(360deg)' },
        },
      },

      // 自定义动画
      animation: {
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in': 'slide-in 0.3s ease-out',
        'bounce-in': 'bounce-in 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'pulse-slow': 'pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin-slow 2s linear infinite',
      },

      // 容器查询支持
      container: {
        center: true,
        padding: {
          DEFAULT: '1rem',
          sm: '1.5rem',
          lg: '2rem',
          xl: '2.5rem',
          '2xl': '3rem',
        },
        screens: {
          sm: '640px',
          md: '768px',
          lg: '1024px',
          xl: '1280px',
          '2xl': '1536px',
        },
      },
    },
  },
  plugins: [
    // 添加一些实用的插件功能
    function({ addUtilities }) {
      const newUtilities = {
        // 截断文本实用工具
        '.text-truncate': {
          overflow: 'hidden',
          'text-overflow': 'ellipsis',
          'white-space': 'nowrap',
        },
        
        // 无滚动条
        '.scrollbar-none': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        
        // 细滚动条
        '.scrollbar-thin': {
          'scrollbar-width': 'thin',
          'scrollbar-color': '#475569 #1e293b',
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#1e293b',
            'border-radius': '3px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#475569',
            'border-radius': '3px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: '#64748b',
          },
        },

        // 背景模糊
        '.backdrop-blur-xs': {
          'backdrop-filter': 'blur(1px)',
        },
        
        // 玻璃态效果
        '.glass': {
          background: 'rgba(30, 41, 59, 0.8)',
          'backdrop-filter': 'blur(10px)',
          border: '1px solid rgba(71, 85, 105, 0.3)',
        },

        // 渐变边框
        '.border-gradient': {
          background: 'linear-gradient(#1e293b, #1e293b) padding-box, linear-gradient(135deg, #3b82f6, #10b981) border-box',
          border: '1px solid transparent',
        },
      }
      
      addUtilities(newUtilities)
    }
  ],
}
