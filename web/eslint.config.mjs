import eslint from "@eslint/js";

export default [
  {
    ignores: [".pnpm-store/**", "coverage/**", "node_modules/**"],
  },
  eslint.configs.recommended,
  {
    files: ["tests/**/*.test.cjs"],
    languageOptions: {
      globals: {
        expect: "readonly",
        test: "readonly",
      },
    },
  },
];
