import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#0f766e",
          green: "#14b8a6",
          ink: "#042f2e",
          mist: "#f0fdfa",
          fog: "#ecfeff",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 0 rgba(255,255,255,0.65) inset, 0 12px 32px -18px rgba(15,23,42,0.18)",
        lift: "0 18px 40px -22px rgba(4,47,46,0.35)",
      },
      backgroundImage: {
        "app-mesh":
          "radial-gradient(ellipse 90% 60% at 0% -10%, rgba(45,212,191,0.22), transparent 55%), radial-gradient(ellipse 70% 50% at 100% 0%, rgba(20,184,166,0.12), transparent 50%), linear-gradient(180deg, #f0fdfa 0%, #f8fafc 42%, #f1f5f9 100%)",
        "ink-hero":
          "linear-gradient(145deg, #042f2e 0%, #0f766e 48%, #2dd4bf 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
