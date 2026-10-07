/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  corePlugins: {
    preflight: false,
  },
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        foreground: "var(--foreground, #1e1c1a)",
        muted: "var(--muted, #f4f4f5)",
        "muted-foreground": "var(--muted-foreground, #71717a)",
      },
    },
  },
  plugins: [],
}
