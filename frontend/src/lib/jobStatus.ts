export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export function getJobStatusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    pending: "Queued",
    running: "Working",
    succeeded: "Complete",
    failed: "Failed",
  };
  return labels[status];
}
