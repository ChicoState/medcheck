import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  use: {
    baseURL: "http://127.0.0.1:5173",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "uv run --project ../backend python ../backend/manage.py migrate --noinput && uv run --project ../backend python ../backend/manage.py runserver 127.0.0.1:8010 --noreload",
      url: "http://127.0.0.1:8010/api/auth/session/",
      reuseExistingServer: false,
    },
    {
      command: "./node_modules/.bin/vite --host 127.0.0.1 --strictPort",
      url: "http://127.0.0.1:5173",
      env: { DJANGO_API_TARGET: "http://127.0.0.1:8010" },
      reuseExistingServer: false,
    },
  ],
});
