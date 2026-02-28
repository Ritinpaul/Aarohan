/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nature: {
          50: '#f2fdf5',
          100: '#e1fbe8',
          200: '#c4f6d4',
          300: '#95ebb3',
          400: '#5dd88c',
          500: '#35be6b',
          600: '#239c51',
          700: '#1e7b42',
          800: '#1b6136',
          900: '#18502e',
          950: '#0c2d19',
        }
      }
    },
  },
  plugins: [],
}
