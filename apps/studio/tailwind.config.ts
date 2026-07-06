import type { Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forge: {
          50: '#f5f7fa',
          300: '#7cc0ff',
          400: '#4aa3ff',
          500: '#2b8cff',
          600: '#1f6fd6',
          900: '#061f37',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
