import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07080d",
        panel: "#10131d",
        line: "#242938",
        gold: "#d8b25d",
        mint: "#50d8a6",
        coral: "#ff7666"
      },
      boxShadow: {
        glow: "0 0 40px rgba(216,178,93,0.12)"
      }
    }
  },
  plugins: []
};

export default config;
