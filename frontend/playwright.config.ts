import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5178', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'android-size', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command:
        'cd ../backend && uv run uvicorn tests.e2e_server:create_e2e_app --factory --host 127.0.0.1 --port 18073 --no-access-log',
      url: 'http://127.0.0.1:18073/api/health',
      reuseExistingServer: false,
    },
    {
      command: 'API_PROXY_TARGET=http://127.0.0.1:18073 npm run dev -- --port 5178 --strictPort',
      url: 'http://127.0.0.1:5178',
      reuseExistingServer: false,
    },
  ],
})
