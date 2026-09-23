import { defineConfig } from "@playwright/test";

// No web server is defined until the application entrypoint exists.
export default defineConfig({ testDir: "tests/e2e" });
