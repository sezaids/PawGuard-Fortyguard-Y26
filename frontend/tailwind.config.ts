import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17312a",
        moss: "#1f725d",
        mint: "#dff6ec",
        sand: "#fbf8f2",
        coral: "#ed775f",
      },
      boxShadow: { card: "0 12px 35px rgba(30, 75, 61, 0.08)" },
    },
  },
  plugins: [],
};

export default config;
