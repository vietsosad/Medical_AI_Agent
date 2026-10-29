import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
    // The timeout catches hangs; it is not a speed gate. Timeline tests step
    // through 14 s of fake time with a render per step, and form tests type
    // with user-event: about 2 s on a desk machine, over the 5 s default on a
    // busy one or on a two-core CI runner.
    testTimeout: 20_000,
  },
});
