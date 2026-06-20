import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          50: '#f0f0f0',
          100: '#e0e0e0',
          200: '#c0c0c0',
          300: '#a0a0a0',
          400: '#808080',
          500: '#606060',
          600: '#404040',
          700: '#2a2a2a',
          800: '#1a1a1a',
          900: '#0d1117',
          950: '#06090e',
        },
        accent: {
          green: '#3fb950',
          red: '#f85149',
          yellow: '#d29922',
          blue: '#58a6ff',
          purple: '#bc8cff',
        },
      },
    },
  },
  plugins: [],
}

export default config
