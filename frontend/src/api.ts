import type { JobStatus } from "./lib/jobStatus";

export type Dataset = {
  id: number;
  source_type: string;
  display_name: string;
  table_schema: string;
  table_name: string;
  row_count: number;
  profile: Record<string, unknown>;
};

export type Job = {
  id: number;
  job_type: "analysis" | "report";
  status: JobStatus;
  input: Record<string, unknown>;
  result: null | {
    conversation_id?: number;
    message?: string;
    artifact_ids?: number[];
  };
  error: string | null;
};

export type Artifact = {
  id: number;
  kind: string;
  title: string;
  mime_type: string;
  payload?: Record<string, unknown> | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function listDatasets(): Promise<Dataset[]> {
  return request<Dataset[]>("/datasets");
}

export function refreshPostgresTables(): Promise<Dataset[]> {
  return request<Dataset[]>("/datasets/postgres/refresh", { method: "POST" });
}

export function uploadDataset(file: File): Promise<Dataset> {
  const body = new FormData();
  body.append("file", file);
  return request<Dataset>("/datasets/upload", { method: "POST", body });
}

export async function deleteDataset(datasetId: number): Promise<void> {
  const response = await fetch(`/api/datasets/${datasetId}`, { method: "DELETE" });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
}

export function createChatJob(message: string, datasetIds: number[], conversationId: number | null): Promise<{ job_id: number }> {
  return request<{ job_id: number }>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, dataset_ids: datasetIds, conversation_id: conversationId }),
  });
}

export function createReportJob(datasetIds: number[], conversationId: number | null): Promise<{ job_id: number }> {
  return request<{ job_id: number }>("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_ids: datasetIds, conversation_id: conversationId }),
  });
}

export function getJob(jobId: number): Promise<Job> {
  return request<Job>(`/jobs/${jobId}`);
}

export function getArtifact(artifactId: number): Promise<Artifact> {
  return request<Artifact>(`/artifacts/${artifactId}/metadata`);
}

export function artifactUrl(artifactId: number): string {
  return `/api/artifacts/${artifactId}/file`;
}
