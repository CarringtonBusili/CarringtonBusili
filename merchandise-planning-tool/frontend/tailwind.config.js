/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9eaff',
          200: '#bcdaff',
          300: '#8ec2ff',
          400: '#589fff',
          500: '#3178f6',
          600: '#1f5aeb',
          700: '#1a47c4',
          800: '#1c3c9c',
          900: '#1c357b',
        },
      },
    },
  },
  plugins: [],
}
