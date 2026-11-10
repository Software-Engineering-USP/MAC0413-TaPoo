/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "sans-serif"] },
      colors: {
        brand: { 50: "#f0f9ff", 100: "#e0f2fe", 500: "#0284c7", 900: "#0c4a6e" },
        risk: { high: "#dc2626", medium: "#f97316", low: "#eab308", safe: "#10b981" },
      },
    },
  },
  plugins: [],
};
