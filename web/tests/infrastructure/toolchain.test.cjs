const packageMetadata = require("../../package.json");

test("web tooling metadata is available", () => {
  expect(packageMetadata.name).toBe("medcheck-web");
});
