import type { Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        forge: {
          50: '#f5f7fa',
          500: '#0d3b66',
          600: '#0a2f52',
          900: '#061f37',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
