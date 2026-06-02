/**
 * @vitest-environment jsdom
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const plotlyMockState = vi.hoisted(() => ({ shouldThrow: false }));

vi.mock("plotly.js/dist/plotly", () => ({
  default: {
    react: vi.fn(async () => {
      if (plotlyMockState.shouldThrow) {
        throw new Error("Plotly failed");
      }
    }),
    purge: vi.fn(),
  },
}));

const uploadedDataset = {
  id: 12,
  source_type: "upload",
  display_name: "sales.csv",
  table_schema: null,
  table_name: null,
  is_imported: false,
  row_count: 2,
  profile: {},
};

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("App dataset upload", () => {
  afterEach(() => {
    cleanup();
    plotlyMockState.shouldThrow = false;
    vi.restoreAllMocks();
  });

  it("shows an uploaded CSV in the data page after upload", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url === "/api/datasets") {
        const listCalls = fetchMock.mock.calls.filter(([callInput]) => callInput.toString() === "/api/datasets").length;
        return jsonResponse(listCalls >= 2 ? [uploadedDataset] : []);
      }
      if (url === "/api/conversations") {
        return jsonResponse([]);
      }
      if (url === "/api/datasets/upload") {
        return jsonResponse(uploadedDataset);
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /data/i }));

    expect(await screen.findByText(/no uploaded csv\/xlsx files yet/i)).toBeInTheDocument();

    const file = new File(["region,revenue\nWest,100\nEast,75\n"], "sales.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText(/upload csv\/xlsx/i), { target: { files: [file] } });

    await waitFor(() => expect(screen.getByText("sales.csv")).toBeInTheDocument());
    expect(screen.getByText(/2 rows - local file/i)).toBeInTheDocument();
  });
});

describe("App chart artifacts", () => {
  afterEach(() => {
    cleanup();
    plotlyMockState.shouldThrow = false;
    vi.restoreAllMocks();
  });

  it("keeps the app visible when Plotly rendering fails", async () => {
    plotlyMockState.shouldThrow = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url === "/api/datasets") {
        return jsonResponse([uploadedDataset]);
      }
      if (url === "/api/conversations") {
        return jsonResponse([]);
      }
      if (url === "/api/chat") {
        return jsonResponse({ job_id: 42 });
      }
      if (url === "/api/jobs/42") {
        return jsonResponse({
          id: 42,
          job_type: "analysis",
          status: "succeeded",
          input: {},
          result: {
            conversation_id: 7,
            message: "Here is the chart.",
            artifact_ids: [99],
          },
          error: null,
        });
      }
      if (url === "/api/artifacts/99/metadata") {
        return jsonResponse({
          id: 99,
          kind: "plotly",
          title: "Sales chart",
          mime_type: "application/vnd.plotly.v1+json",
          payload: {
            data: [{ type: "bar", x: ["West"], y: [100] }],
            layout: { title: "Sales chart" },
          },
        });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.change(await screen.findByPlaceholderText(/ask for analysis/i), {
      target: { value: "draw a chart" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));

    await waitFor(() => expect(screen.getByText("Here is the chart.")).toBeInTheDocument(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText(/chart rendering failed/i)).toBeInTheDocument(), { timeout: 3000 });
    expect(screen.getByText("AI Data Analyst")).toBeInTheDocument();
  });
});
