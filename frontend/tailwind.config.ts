import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "hsl(var(--canvas))",
        surface: "hsl(var(--surface))",
        ink: "hsl(var(--ink))",
        muted: "hsl(var(--muted))",
        line: "hsl(var(--line))",
        accent: "hsl(var(--accent))",
      },
      boxShadow: { soft: "0 1px 2px rgba(27, 25, 22, .04), 0 10px 35px rgba(27, 25, 22, .035)" },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"], serif: ["Newsreader", "Iowan Old Style", "serif"] },
    },
  },
  plugins: [],
} satisfies Config;
