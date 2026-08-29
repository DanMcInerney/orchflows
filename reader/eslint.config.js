import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["web/dist/**"] },
  ...tseslint.configs.recommended,
  {
    files: ["web/src/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }]
    }
  }
);
