/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medical: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7ccbfd',
          400: '#36b3fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        status: {
          pass: '#10b981',
          passBg: '#d1fae5',
          passLight: '#ecfdf5',
          fail: '#ef4444',
          failBg: '#fee2e2',
          failLight: '#fef2f2',
          warn: '#f59e0b',
          warnBg: '#fef3c7',
          warnLight: '#fffbeb',
          info: '#6b7280',
          infoBg: '#f3f4f6',
          infoLight: '#f9fafb',
        },
        surface: {
          primary: '#ffffff',
          secondary: '#f8fafc',
          tertiary: '#f1f5f9',
          elevated: '#ffffff',
        },
        glass: {
          bg: 'rgba(255, 255, 255, 0.7)',
          border: 'rgba(255, 255, 255, 0.3)',
          shadow: 'rgba(0, 0, 0, 0.05)',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
        mono: ['"SF Mono"', 'Monaco', 'Inconsolata', '"Roboto Mono"', 'monospace'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 1px 3px 0 rgb(0 0 0 / 0.1)',
        'soft-lg': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
        'soft-xl': '0 10px 15px -3px rgb(0 0 0 / 0.1)',
        'glow': '0 0 20px rgba(59, 130, 246, 0.15)',
        'glow-pass': '0 0 20px rgba(16, 185, 129, 0.15)',
        'glow-fail': '0 0 20px rgba(239, 68, 68, 0.15)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'fade-in-up': 'fadeInUp 0.4s ease-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%': { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      transitionTimingFunction: {
        'bounce-soft': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
