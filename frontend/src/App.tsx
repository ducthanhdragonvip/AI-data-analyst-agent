import { BarChart3, Database, FileUp, RefreshCw, Send, FileText, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Data, Layout } from "plotly.js";
import Plot from "react-plotly.js";
import ReactMarkdown from "react-markdown";

import {
  artifactUrl,
  createChatJob,
  createReportJob,
  deleteDataset,
  getArtifact,
  getJob,
  importDatasetToDatabase,
  listDatasets,
  refreshPostgresTables,
  uploadDataset,
  type Artifact,
  type Dataset,
  type Job,
} from "./api";
import { getJobStatusLabel } from "./lib/jobStatus";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  artifactIds?: number[];
};

function App() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<number[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "system",
      content: "Select a dataset, then ask for analysis, a chart, or a Markdown report.",
    },
  ]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [artifacts, setArtifacts] = useState<Record<number, Artifact>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDatasets();
  }, []);

  useEffect(() => {
    if (!activeJob || activeJob.status === "succeeded" || activeJob.status === "failed") {
      return;
    }
    const timer = window.setInterval(async () => {
      const job = await getJob(activeJob.id);
      setActiveJob(job);
      if (job.status === "succeeded") {
        const artifactIds = job.result?.artifact_ids ?? [];
        setConversationId(job.result?.conversation_id ?? conversationId);
        setMessages((current) => [
          ...current,
          {
            id: `job-${job.id}`,
            role: "assistant",
            content: job.result?.message ?? "Analysis complete.",
            artifactIds,
          },
        ]);
        await Promise.all(
          artifactIds.map(async (artifactId) => {
            const artifact = await getArtifact(artifactId);
            setArtifacts((current) => ({ ...current, [artifactId]: artifact }));
          })
        );
      }
      if (job.status === "failed") {
        setMessages((current) => [
          ...current,
          { id: `job-${job.id}-failed`, role: "system", content: job.error ?? "Job failed." },
        ]);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [activeJob, conversationId]);

  const selectedDatasets = useMemo(
    () => datasets.filter((dataset) => selectedDatasetIds.includes(dataset.id)),
    [datasets, selectedDatasetIds]
  );

  async function loadDatasets() {
    try {
      setDatasets(await listDatasets());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load datasets");
    }
  }

  async function handleUpload(file: File | null) {
    if (!file) return;
    setError(null);
    const dataset = await uploadDataset(file);
    setDatasets((current) => [dataset, ...current]);
    setSelectedDatasetIds((current) => [...new Set([...current, dataset.id])]);
  }

  async function handleRefresh() {
    setError(null);
    await refreshPostgresTables();
    await loadDatasets();
  }

  async function handleImportDataset(datasetId: number) {
    setError(null);
    const imported = await importDatasetToDatabase(datasetId);
    setDatasets((current) => current.map((dataset) => (dataset.id === imported.id ? imported : dataset)));
    setSelectedDatasetIds((current) => [...new Set([...current, imported.id])]);
  }

  async function handleDeleteDataset(datasetId: number) {
    setError(null);
    await deleteDataset(datasetId);
    setDatasets((current) => current.filter((dataset) => dataset.id !== datasetId));
    setSelectedDatasetIds((current) => current.filter((id) => id !== datasetId));
  }

  async function submitChat() {
    const message = input.trim();
    if (!message || activeJob?.status === "pending" || activeJob?.status === "running") return;
    setInput("");
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: message }]);
    const jobRef = await createChatJob(message, selectedDatasetIds, conversationId);
    setActiveJob(await getJob(jobRef.job_id));
  }

  async function submitReport() {
    if (activeJob?.status === "pending" || activeJob?.status === "running") return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: "Generate a Markdown report." }]);
    const jobRef = await createReportJob(selectedDatasetIds, conversationId);
    setActiveJob(await getJob(jobRef.job_id));
  }

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <BarChart3 size={22} />
          <span>AI Data Analyst</span>
        </div>

        <label className="uploadButton">
          <FileUp size={18} />
          <span>Upload CSV/XLSX</span>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => void handleUpload(event.target.files?.[0] ?? null)} />
        </label>

        <button className="secondaryButton" onClick={() => void handleRefresh()}>
          <RefreshCw size={17} />
          <span>Refresh Postgres</span>
        </button>

        <section className="datasetList" aria-label="Datasets">
          {datasets.map((dataset) => (
            <div className="datasetItem" key={dataset.id}>
              <input
                type="checkbox"
                checked={selectedDatasetIds.includes(dataset.id)}
                onChange={(event) => {
                  setSelectedDatasetIds((current) =>
                    event.target.checked ? [...current, dataset.id] : current.filter((id) => id !== dataset.id)
                  );
                }}
              />
              <Database size={16} />
              <span>
                <strong>{dataset.display_name}</strong>
                <small>
                  {dataset.row_count.toLocaleString()} rows
                  {dataset.is_imported ? " saved to DB" : " local file"}
                </small>
              </span>
              {!dataset.is_imported && (
                <button
                  className="textButton"
                  type="button"
                  onClick={() => void handleImportDataset(dataset.id)}
                >
                  Save to DB
                </button>
              )}
              <button
                className="iconButton"
                type="button"
                aria-label={`Remove ${dataset.display_name}`}
                title="Remove dataset"
                onClick={() => void handleDeleteDataset(dataset.id)}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </section>
      </aside>

      <section className="chatPanel">
        <header className="chatHeader">
          <div>
            <h1>Analyst Chat</h1>
            <p>{selectedDatasets.length ? selectedDatasets.map((dataset) => dataset.display_name).join(", ") : "No dataset selected"}</p>
          </div>
          <button className="secondaryButton" onClick={() => void submitReport()}>
            <FileText size={17} />
            <span>Report</span>
          </button>
        </header>

        {error && <div className="errorBox">{error}</div>}

        <div className="messages">
          {messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {message.artifactIds?.map((artifactId) => (
                <ArtifactView artifact={artifacts[artifactId]} artifactId={artifactId} key={artifactId} />
              ))}
            </article>
          ))}
          {activeJob && activeJob.status !== "succeeded" && activeJob.status !== "failed" && (
            <article className="message system">{getJobStatusLabel(activeJob.status)}...</article>
          )}
        </div>

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            void submitChat();
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask for analysis, a chart, or a follow-up..."
          />
          <button type="submit" aria-label="Send message">
            <Send size={18} />
          </button>
        </form>
      </section>
    </main>
  );
}

function ArtifactView({ artifact, artifactId }: { artifact?: Artifact; artifactId: number }) {
  if (!artifact) {
    return <div className="artifact">Loading artifact...</div>;
  }
  if (artifact.kind === "plotly" && artifact.payload) {
    const payload = artifact.payload as { data?: Data[]; layout?: Partial<Layout> };
    return (
      <div className="artifact">
        <Plot data={payload.data ?? []} layout={{ ...(payload.layout ?? {}), autosize: true }} useResizeHandler className="plot" />
      </div>
    );
  }
  if (artifact.mime_type === "image/png") {
    return <img className="chartImage" src={artifactUrl(artifactId)} alt={artifact.title} />;
  }
  return (
    <a className="downloadLink" href={artifactUrl(artifactId)}>
      Download {artifact.title}
    </a>
  );
}

export default App;
