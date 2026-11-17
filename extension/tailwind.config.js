/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./sidepanel.html"
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        dark: {
          950: "#070a12",
          900: "#0b1120",
          850: "#111827",
          800: "#172033",
          700: "#1e293b",
          600: "#334155"
        },
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca"
        }
      }
    }
  },
  plugins: []
};
