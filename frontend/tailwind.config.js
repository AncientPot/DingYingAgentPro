/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        base: {
          900: '#08080f',
          850: '#0e0e18',
          800: '#141422',
          750: '#1a1a2c',
          700: '#222238',
        },
        accent: {
          DEFAULT: '#00e5ff',
          glow: '#00e5ff33',
          dim: '#00b8d4',
        },
        amber: {
          tool: '#ffb74d',
        },
        surface: {
          DEFAULT: 'rgba(255,255,255,0.05)',
          hover: 'rgba(255,255,255,0.09)',
          border: 'rgba(255,255,255,0.08)',
        },
      },
      fontFamily: {
        display: ['"PingFang SC"', '"Microsoft YaHei"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"Cascadia Code"', '"Fira Code"', '"Sarasa Gothic"', 'ui-monospace', 'monospace'],
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
        'cursor-blink': 'cursor-blink 1s step-end infinite',
        'scan-line': 'scan-line 8s linear infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0,229,255,0.15)' },
          '50%': { boxShadow: '0 0 35px rgba(0,229,255,0.3)' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'cursor-blink': {
          '50%': { opacity: '0' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
    },
  },
  plugins: [],
}
