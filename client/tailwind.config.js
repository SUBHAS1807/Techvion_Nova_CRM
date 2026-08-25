/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        crm: {
          black: '#0A0A0A',
          dark: '#171717',
          gray: '#737373',
          light: '#F5F5F5',
          border: '#E5E5E5',
        }
      }
    },
  },
  plugins: [],
}
