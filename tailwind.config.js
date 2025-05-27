/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#08b9ff',
          dark: '#0696cc',
        },
        background: {
          DEFAULT: '#1c0c04',
          secondary: '#120709',
        },
        text: {
          DEFAULT: '#ffc666',
        },
      },
    },
  },
  plugins: [],
}