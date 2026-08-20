import { describe, expect, it } from "vitest";

import { API_BASE_URL } from "./client";

describe("API client scaffold", () => {
  it("has a local development fallback", () => {
    expect(API_BASE_URL).toContain("localhost");
  });
});
