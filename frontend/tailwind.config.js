/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Legacy (used by dashboard/login/register pages)
        primary: { 50: '#eef2ff', 100: '#e0e7ff', 500: '#4f60cc', 600: '#3346AC', 700: '#2a3a9e', 800: '#1e2d8c' },
        navy: { 900: '#050F2E', 800: '#081F5C', 700: '#0B2770' },
        brand: { green: '#95ffb7' },
        // New design system tokens
        surface: '#f9f9ff',
        'surface-container':       '#e7eeff',
        'surface-container-low':   '#f0f3ff',
        'surface-container-high':  '#dee8ff',
        'surface-container-highest':'#d5e3ff',
        'on-surface':          '#001b3b',
        'on-surface-variant':  '#454652',
        'outline-variant':     '#c5c5d5',
        'outline':             '#757684',
        'primary-deep':        '#081F5C',
        'primary-mid':         '#162c94',
        'primary-btn':         '#3346AC',
        'primary-container':   '#dee0ff',
        'secondary-green':     '#006d33',
        'secondary-container': '#8ff5a6',
        'on-secondary-container': '#007236',
      },
      fontFamily: {
        display: ["'Sora'", 'sans-serif'],
        body:    ["'Inter'", 'sans-serif'],
        kufi:    ["'Noto Kufi Arabic'", 'sans-serif'],
      },
      maxWidth: {
        container: '1280px',
      },
      spacing: {
        desktop: '64px',
        mobile:  '20px',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
