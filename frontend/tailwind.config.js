/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f8f4f7',
          100: '#f1e8ef',
          200: '#dfcddd',
          300: '#c7a8c1',
          400: '#a17c99',
          500: '#714b67',
          600: '#623f59',
          700: '#54354c',
          800: '#452c40',
          900: '#372332',
        },
      },
    },
  },
  plugins: [],
}
