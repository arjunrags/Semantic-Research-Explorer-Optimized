/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        void: '#050508',
        surface: '#0d0d14',
        panel: '#11111c',
        border: '#1e1e2e',
        accent: '#7c6af7',
        'accent-glow': '#9d8fff',
        amber: '#f4a261',
        emerald: '#2dd4bf',
        rose: '#fb7185',
        muted: '#4a4a6a',
        dim: '#2a2a3e',
      },
      boxShadow: {
        glow: '0 0 20px rgba(124, 106, 247, 0.3)',
        'glow-sm': '0 0 10px rgba(124, 106, 247, 0.2)',
        'glow-amber': '0 0 20px rgba(244, 162, 97, 0.3)',
        'glow-rose': '0 0 20px rgba(251, 113, 133, 0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'slide-in': 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-up': 'fadeUp 0.4s ease-out',
      },
      keyframes: {
        slideIn: {
          from: { transform: 'translateX(100%)', opacity: 0 },
          to: { transform: 'translateX(0)', opacity: 1 },
        },
        fadeUp: {
          from: { transform: 'translateY(8px)', opacity: 0 },
          to: { transform: 'translateY(0)', opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}
