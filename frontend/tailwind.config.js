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
          50: '#faf5f9',
          100: '#f2eaf0',
          200: '#e3d2df',
          300: '#ccadc4',
          400: '#ab83a2',
          500: '#8d6483',
          600: '#714b67',
          700: '#593a51',
          800: '#422b3d',
          900: '#2f202d',
        },
        teal: { 50: '#edf8f8', 100: '#d9eeed', 600: '#017e84', 700: '#00696e' },
      },
    },
  },
  plugins: [],
}
