import type { Config } from "tailwindcss";

// Única fuente de color de la interfaz. No uses hex sueltos en los componentes:
// si falta un tono, añádelo aquí y documéntalo en docs/design/README.md.
//
// Cada tono de estado tiene la misma forma:
//   DEFAULT → texto e iconos sobre fondo claro
//   soft    → fondo de avisos y etiquetas
//   line    → borde de avisos
//   bright  → puntos, barras y gráficos (no para texto pequeño)
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: "#F5F4EF", soft: "#FAF9F5", deep: "#ECEAE2" },
        ink: {
          DEFAULT: "#15171C",
          soft: "#23262D",
          line: "#343842",
          active: "#2A2E36",
          raised: "#3B4049",
          // Texto sobre fondo ink, de más a menos énfasis
          fg: "#E9E7E0",
          dim: "#C9CCD3",
          faint: "#A9ADB6",
        },
        muted: "#555B66",
        line: { DEFAULT: "#DEDBD2", strong: "#C9C5B9" },
        lexi: { DEFAULT: "#0E5A55", dark: "#08403C", soft: "#E6F1EF", line: "#B7D6D2", bright: "#1F7A68" },
        warn: { DEFAULT: "#7A5600", soft: "#FFF3D6", line: "#EAD7A5", bright: "#C98A12" },
        danger: { DEFAULT: "#9A2D20", soft: "#FBE9E7", line: "#E7B8B1", bright: "#B3372A" },
        info: { DEFAULT: "#3F4B66", soft: "#EEF0F5", line: "#CDD3E0", bright: "#5B6B7A" },
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
