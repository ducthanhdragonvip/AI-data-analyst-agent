import {
  BarChart3,
  Database,
  FileText,
  FileUp,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  TableProperties,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Data, Layout } from "plotly.js";
import Plot from "react-plotly.js";
import ReactMarkdown from "react-markdown";

import {
  artifactUrl,
  createChatJob,
  createReportJob,
  deleteConversation,
  deleteDataset,
  getArtifact,
  getConversation,
  getJob,
  importDatasetToDatabase,
  listConversations,
  listDatasets,
  refreshPostgresTables,
  uploadDataset,
  type Artifact,
  type ConversationSummary,
  type Dataset,
  type Job,
} from "./api";
import { getJobStatusLabel } from "./lib/jobStatus";

type ViewName = "chat" | "data";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  artifactIds?: number[];
};

const welcomeMessage: ChatMessage = {
  id: "welcome",
  role: "system",
  content: "Select a dataset, then ask for analysis, a chart, or a Markdown report.",
};

function App() {
  const [view, setView] = useState<ViewName>("chat");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<number[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [artifacts, setArtifacts] = useState<Record<number, Artifact>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDatasets();
    void loadConversations();
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
        const nextConversationId = job.result?.conversation_id ?? conversationId;
        setConversationId(nextConversationId);
        setMessages((current) => [
          ...current,
          {
            id: `job-${job.id}`,
            role: "assistant",
            content: job.result?.message ?? "Analysis complete.",
            artifactIds,
          },
        ]);
        await loadArtifacts(artifactIds);
        await loadConversations();
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

  async function loadConversations() {
    try {
      setConversations(await listConversations());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load conversations");
    }
  }

  async function loadArtifacts(artifactIds: number[]) {
    await Promise.all(
      artifactIds.map(async (artifactId) => {
        const artifact = await getArtifact(artifactId);
        setArtifacts((current) => ({ ...current, [artifactId]: artifact }));
      })
    );
  }

  async function openConversation(id: number) {
    setError(null);
    const conversation = await getConversation(id);
    setConversationId(conversation.id);
    const loadedMessages = conversation.messages.map((message) => ({
      id: `message-${message.id}`,
      role: message.role,
      content: message.content,
      artifactIds: message.artifact_ids,
    }));
    setMessages(loadedMessages.length ? loadedMessages : [welcomeMessage]);
    await loadArtifacts(conversation.messages.flatMap((message) => message.artifact_ids));
    setView("chat");
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([welcomeMessage]);
    setActiveJob(null);
    setInput("");
    setView("chat");
  }

  async function handleDeleteConversation(id: number) {
    setError(null);
    await deleteConversation(id);
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
    if (conversationId === id) {
      startNewConversation();
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

        <nav className="navButtons" aria-label="Primary">
          <button className={view === "chat" ? "navButton active" : "navButton"} onClick={() => setView("chat")}>
            <MessageSquare size={17} />
            <span>Chat</span>
          </button>
          <button className={view === "data" ? "navButton active" : "navButton"} onClick={() => setView("data")}>
            <TableProperties size={17} />
            <span>Data</span>
          </button>
        </nav>

        <button className="secondaryButton" onClick={startNewConversation}>
          <Plus size={17} />
          <span>New Chat</span>
        </button>

        <section className="historyList" aria-label="Recent conversations">
          <div className="sectionLabel">Recent</div>
          {conversations.map((conversation) => (
            <div
              className={conversation.id === conversationId ? "historyItem active" : "historyItem"}
              key={conversation.id}
            >
              <button className="historyOpen" type="button" onClick={() => void openConversation(conversation.id)}>
                <strong>{conversation.title}</strong>
                <small>{conversation.message_count} messages</small>
              </button>
              <button
                className="historyDelete"
                type="button"
                aria-label={`Delete ${conversation.title}`}
                title="Delete conversation"
                onClick={() => void handleDeleteConversation(conversation.id)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </section>
      </aside>

      {view === "chat" ? (
        <ChatView
          activeJob={activeJob}
          artifacts={artifacts}
          datasets={datasets}
          input={input}
          messages={messages}
          selectedDatasetIds={selectedDatasetIds}
          selectedDatasets={selectedDatasets}
          error={error}
          onInput={setInput}
          onReport={() => void submitReport()}
          onSubmit={() => void submitChat()}
          onToggleDataset={(datasetId, checked) => {
            setSelectedDatasetIds((current) =>
              checked ? [...current, datasetId] : current.filter((id) => id !== datasetId)
            );
          }}
        />
      ) : (
        <DataView
          datasets={datasets}
          error={error}
          onDelete={(datasetId) => void handleDeleteDataset(datasetId)}
          onImport={(datasetId) => void handleImportDataset(datasetId)}
          onRefresh={() => void handleRefresh()}
          onUpload={(file) => void handleUpload(file)}
        />
      )}
    </main>
  );
}

function ChatView({
  activeJob,
  artifacts,
  datasets,
  error,
  input,
  messages,
  selectedDatasetIds,
  selectedDatasets,
  onInput,
  onReport,
  onSubmit,
  onToggleDataset,
}: {
  activeJob: Job | null;
  artifacts: Record<number, Artifact>;
  datasets: Dataset[];
  error: string | null;
  input: string;
  messages: ChatMessage[];
  selectedDatasetIds: number[];
  selectedDatasets: Dataset[];
  onInput: (value: string) => void;
  onReport: () => void;
  onSubmit: () => void;
  onToggleDataset: (datasetId: number, checked: boolean) => void;
}) {
  return (
    <section className="chatPanel">
      <header className="chatHeader">
        <div>
          <h1>Analyst Chat</h1>
          <p>{selectedDatasets.length ? selectedDatasets.map((dataset) => dataset.display_name).join(", ") : "No dataset selected"}</p>
        </div>
        <button className="secondaryButton" onClick={onReport}>
          <FileText size={17} />
          <span>Report</span>
        </button>
      </header>

      <section className="datasetStrip" aria-label="Selectable datasets">
        {datasets.map((dataset) => (
          <label className="datasetChip" key={dataset.id}>
            <input
              type="checkbox"
              checked={selectedDatasetIds.includes(dataset.id)}
              onChange={(event) => onToggleDataset(dataset.id, event.target.checked)}
            />
            <span>{dataset.display_name}</span>
          </label>
        ))}
      </section>

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
          onSubmit();
        }}
      >
        <input value={input} onChange={(event) => onInput(event.target.value)} placeholder="Ask for analysis, a chart, or a follow-up..." />
        <button type="submit" aria-label="Send message">
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}

function DataView({
  datasets,
  error,
  onDelete,
  onImport,
  onRefresh,
  onUpload,
}: {
  datasets: Dataset[];
  error: string | null;
  onDelete: (datasetId: number) => void;
  onImport: (datasetId: number) => void;
  onRefresh: () => void;
  onUpload: (file: File | null) => void;
}) {
  return (
    <section className="dataPanel">
      <header className="chatHeader">
        <div>
          <h1>Data</h1>
          <p>Upload local files, import staged files, or refresh Postgres tables.</p>
        </div>
        <button className="secondaryButton" onClick={onRefresh}>
          <RefreshCw size={17} />
          <span>Refresh Postgres</span>
        </button>
      </header>

      {error && <div className="errorBox">{error}</div>}

      <div className="dataActions">
        <label className="uploadButton">
          <FileUp size={18} />
          <span>Upload CSV/XLSX</span>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => onUpload(event.target.files?.[0] ?? null)} />
        </label>
      </div>

      <section className="dataList" aria-label="Datasets">
        {datasets.map((dataset) => (
          <div className="dataRow" key={dataset.id}>
            <Database size={18} />
            <span>
              <strong>{dataset.display_name}</strong>
              <small>
                {dataset.row_count.toLocaleString()} rows · {dataset.is_imported ? `DB table ${dataset.table_name}` : "local file"}
              </small>
            </span>
            {!dataset.is_imported && (
              <button className="textButton" type="button" onClick={() => onImport(dataset.id)}>
                Save to DB
              </button>
            )}
            <button className="iconButton" type="button" aria-label={`Remove ${dataset.display_name}`} title="Remove dataset" onClick={() => onDelete(dataset.id)}>
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </section>
    </section>
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
