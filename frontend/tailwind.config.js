/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f2f6ff",
          100: "#e2ebff",
          500: "#4f6df5",
          600: "#3c54d6",
          700: "#2f42ab",
        },
      },
    },
  },
  plugins: [],
};
