import type { JobStatus } from "./lib/jobStatus";

export type Dataset = {
  id: number;
  source_type: string;
  display_name: string;
  table_schema: string | null;
  table_name: string | null;
  is_imported: boolean;
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

export type ConversationSummary = {
  id: number;
  title: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
};

export type ConversationMessage = {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  artifact_ids: number[];
  created_at: string;
};

export type ConversationDetail = {
  id: number;
  title: string;
  created_at: string;
  messages: ConversationMessage[];
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

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/conversations");
}

export function getConversation(conversationId: number): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${conversationId}`);
}

export async function deleteConversation(conversationId: number): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}`, { method: "DELETE" });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
}

export function refreshPostgresTables(): Promise<Dataset[]> {
  return request<Dataset[]>("/datasets/postgres/refresh", { method: "POST" });
}

export function uploadDataset(file: File): Promise<Dataset> {
  const body = new FormData();
  body.append("file", file);
  return request<Dataset>("/datasets/upload", { method: "POST", body });
}

export function importDatasetToDatabase(datasetId: number): Promise<Dataset> {
  return request<Dataset>(`/datasets/${datasetId}/import`, { method: "POST" });
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
