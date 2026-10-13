import type { Config } from "tailwindcss";

// Tokens tomados de los mockups (docs/design/README.md)
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F5F4EF",
        ink: { DEFAULT: "#15171C", soft: "#23262D", line: "#343842" },
        muted: "#555B66",
        line: "#DEDBD2",
        lexi: { DEFAULT: "#0E5A55", dark: "#08403C", soft: "#E3EFEC" },
        warn: { DEFAULT: "#7A3D0B", soft: "#FBEEDD" },
        danger: { DEFAULT: "#8A1F16", soft: "#F8E3DF" },
        info: { DEFAULT: "#1B4479", soft: "#E3ECF6" },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Helvetica Neue", "sans-serif"],
        mono: ["var(--font-mono)", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
