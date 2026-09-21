/** Infrastructure-only Jest configuration; application test setup comes later. */
module.exports = {
  collectCoverageFrom: ["tests/infrastructure/**/*.cjs"],
  testMatch: ["<rootDir>/tests/**/*.test.cjs"],
};
