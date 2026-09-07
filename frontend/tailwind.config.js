/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        pine: { DEFAULT: "#1b3d2f", 2: "#244a3a" },
        copper: { DEFAULT: "#b08d57", 2: "#c9a66b" },
        paper: { DEFAULT: "#e7eee8", 2: "#f3f7f3" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "Georgia", "serif"],
        body: ['"IBM Plex Sans"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
