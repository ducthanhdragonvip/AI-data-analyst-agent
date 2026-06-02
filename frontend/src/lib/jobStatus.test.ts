import { describe, expect, it } from "vitest";

import { getJobStatusLabel } from "./jobStatus";

describe("getJobStatusLabel", () => {
  it("maps API job statuses to user-facing labels", () => {
    expect(getJobStatusLabel("pending")).toBe("Queued");
    expect(getJobStatusLabel("running")).toBe("Working");
    expect(getJobStatusLabel("succeeded")).toBe("Complete");
    expect(getJobStatusLabel("failed")).toBe("Failed");
  });
});
