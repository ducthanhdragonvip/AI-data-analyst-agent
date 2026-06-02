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
import { Component, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Data, Layout } from "plotly.js";
import * as PlotlyModule from "plotly.js/dist/plotly";
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

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

const focusRing =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-violet-200";
const interactive = `cursor-pointer transition-colors duration-200 ${focusRing}`;
const iconButton =
  `inline-grid h-[30px] w-[30px] place-items-center rounded-lg border border-zinc-200 bg-white text-zinc-600 hover:border-violet-200 hover:bg-white hover:text-violet-800 ${interactive}`;
const secondaryButton =
  `inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 text-zinc-900 hover:border-violet-200 hover:text-violet-800 ${interactive}`;
const uploadButton =
  `inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-violet-600 bg-violet-600 px-3 text-white hover:border-violet-800 hover:bg-violet-800 ${interactive}`;
const panelHeader =
  "flex items-center justify-between gap-3.5 border-b border-zinc-200 bg-white/75 px-6 py-[18px] max-[560px]:flex-col max-[560px]:items-start max-[560px]:px-3.5";
const panelTitle = "m-0 text-[22px] font-[850] tracking-normal text-zinc-900 max-[560px]:text-xl";
const panelSubtitle = "mt-1 mb-0 text-zinc-600";

type PlotlyApi = {
  react: (element: HTMLElement, data: Data[], layout?: Partial<Layout>, config?: Record<string, unknown>) => Promise<unknown>;
  purge: (element: HTMLElement) => void;
};

const Plotly = ((PlotlyModule as { default?: PlotlyApi }).default ?? (PlotlyModule as unknown as PlotlyApi)) as PlotlyApi;

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
  const [isUploading, setIsUploading] = useState(false);

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
      await handleJobUpdate(job);
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

  async function handleJobUpdate(job: Job) {
    setActiveJob(job);
    if (job.status === "succeeded") {
      const artifactIds = job.result?.artifact_ids ?? [];
      const nextConversationId = job.result?.conversation_id ?? conversationId;
      setConversationId(nextConversationId);
      setMessages((current) => {
        if (current.some((message) => message.id === `job-${job.id}`)) {
          return current;
        }
        return [
          ...current,
          {
            id: `job-${job.id}`,
            role: "assistant",
            content: job.result?.message ?? "Analysis complete.",
            artifactIds,
          },
        ];
      });
      await loadArtifacts(artifactIds);
      await loadConversations();
    }
    if (job.status === "failed") {
      setMessages((current) => {
        if (current.some((message) => message.id === `job-${job.id}-failed`)) {
          return current;
        }
        return [...current, { id: `job-${job.id}-failed`, role: "system", content: job.error ?? "Job failed." }];
      });
    }
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
    setIsUploading(true);
    try {
      const dataset = await uploadDataset(file);
      await loadDatasets();
      setSelectedDatasetIds((current) => [...new Set([...current, dataset.id])]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not upload dataset");
    } finally {
      setIsUploading(false);
    }
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
    await handleJobUpdate(await getJob(jobRef.job_id));
  }

  async function submitReport() {
    if (activeJob?.status === "pending" || activeJob?.status === "running") return;
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: "user", content: "Generate a Markdown report." }]);
    const jobRef = await createReportJob(selectedDatasetIds, conversationId);
    await handleJobUpdate(await getJob(jobRef.job_id));
  }

  return (
    <main className="grid min-h-screen grid-cols-[292px_minmax(0,1fr)] text-zinc-900 max-[820px]:grid-cols-1">
      <aside className="flex flex-col gap-3 border-r border-zinc-200 bg-white/85 p-4 max-[820px]:max-h-[300px] max-[820px]:border-r-0 max-[820px]:border-b">
        <div className="flex min-h-10 items-center gap-2.5 font-extrabold">
          <BarChart3 className="text-violet-600" size={22} />
          <span>AI Data Analyst</span>
        </div>

        <nav className="grid grid-cols-2 gap-2" aria-label="Primary">
          <button
            className={cx(
              `inline-flex min-h-[38px] items-center justify-center gap-2 rounded-lg border px-3 ${interactive}`,
              view === "chat"
                ? "border-violet-200 bg-violet-50 text-violet-800"
                : "border-zinc-200 bg-transparent text-zinc-600 hover:border-violet-200 hover:bg-violet-50 hover:text-violet-800"
            )}
            onClick={() => setView("chat")}
          >
            <MessageSquare size={17} />
            <span>Chat</span>
          </button>
          <button
            className={cx(
              `inline-flex min-h-[38px] items-center justify-center gap-2 rounded-lg border px-3 ${interactive}`,
              view === "data"
                ? "border-violet-200 bg-violet-50 text-violet-800"
                : "border-zinc-200 bg-transparent text-zinc-600 hover:border-violet-200 hover:bg-violet-50 hover:text-violet-800"
            )}
            onClick={() => setView("data")}
          >
            <TableProperties size={17} />
            <span>Data</span>
          </button>
        </nav>

        <button className={secondaryButton} onClick={startNewConversation}>
          <Plus size={17} />
          <span>New Chat</span>
        </button>

        <section className="grid min-h-0 gap-2 overflow-auto pt-1" aria-label="Recent conversations">
          <div className="text-xs font-extrabold tracking-normal text-zinc-500 uppercase">Recent</div>
          {conversations.map((conversation) => (
            <div
              className={cx(
                "grid w-full grid-cols-[minmax(0,1fr)_30px] items-center gap-1.5 rounded-lg border p-2 text-zinc-900",
                conversation.id === conversationId
                  ? "border-violet-200 bg-violet-50"
                  : "border-transparent bg-transparent hover:border-violet-200 hover:bg-violet-50"
              )}
              key={conversation.id}
            >
              <button
                className={`grid min-w-0 gap-0.5 border-0 bg-transparent text-left text-inherit ${interactive}`}
                type="button"
                onClick={() => void openConversation(conversation.id)}
              >
                <strong className="overflow-hidden text-ellipsis whitespace-nowrap text-sm">{conversation.title}</strong>
                <small className="overflow-hidden text-ellipsis whitespace-nowrap text-xs text-zinc-600">
                  {conversation.message_count} messages
                </small>
              </button>
              <button
                className={iconButton}
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
          isUploading={isUploading}
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
    <section className="grid max-h-screen min-w-0 grid-rows-[auto_auto_1fr_auto] max-[820px]:min-h-[calc(100vh-300px)] max-[820px]:max-h-none">
      <header className={panelHeader}>
        <div>
          <h1 className={panelTitle}>Analyst Chat</h1>
          <p className={panelSubtitle}>
            {selectedDatasets.length ? selectedDatasets.map((dataset) => dataset.display_name).join(", ") : "No dataset selected"}
          </p>
        </div>
        <button className={secondaryButton} onClick={onReport}>
          <FileText size={17} />
          <span>Report</span>
        </button>
      </header>

      <section
        className="flex gap-2 overflow-x-auto border-b border-zinc-200 bg-zinc-50/90 px-6 py-2.5 max-[560px]:px-3.5"
        aria-label="Selectable datasets"
      >
        {datasets.map((dataset) => (
          <label
            className={`inline-flex min-h-8 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-lg border border-zinc-200 bg-white px-2.5 text-zinc-700 transition-colors duration-200 has-[:checked]:border-violet-300 has-[:checked]:bg-violet-50 has-[:checked]:text-violet-800 ${focusRing}`}
            key={dataset.id}
          >
            <input
              type="checkbox"
              checked={selectedDatasetIds.includes(dataset.id)}
              onChange={(event) => onToggleDataset(dataset.id, event.target.checked)}
            />
            <span>{dataset.display_name}</span>
          </label>
        ))}
      </section>

      {error && <div className="mx-6 mt-3.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-rose-800">{error}</div>}

      <div className="flex min-h-0 flex-col gap-3 overflow-auto p-6 max-[560px]:px-3.5">
        {messages.map((message) => (
          <article
            className={cx(
              "max-w-[940px] rounded-lg px-[15px] py-[13px] leading-[1.48] [&_p]:m-0",
              message.role === "user" && "self-end bg-violet-600 text-white",
              message.role === "assistant" && "self-start border border-zinc-200 bg-white text-zinc-900",
              message.role === "system" && "self-center border border-violet-200 bg-violet-50 text-violet-800"
            )}
            key={message.id}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.artifactIds?.map((artifactId) => (
              <ArtifactView artifact={artifacts[artifactId]} artifactId={artifactId} key={artifactId} />
            ))}
          </article>
        ))}
        {activeJob && activeJob.status !== "succeeded" && activeJob.status !== "failed" && (
          <article className="self-center rounded-lg border border-violet-200 bg-violet-50 px-[15px] py-[13px] leading-[1.48] text-violet-800">
            {getJobStatusLabel(activeJob.status)}...
          </article>
        )}
      </div>

      <form
        className="grid grid-cols-[minmax(0,1fr)_44px] gap-2.5 border-t border-zinc-200 bg-white/90 px-6 pt-4 pb-5 max-[560px]:px-3.5"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <input
          className={`h-11 min-w-0 rounded-lg border border-zinc-200 bg-white px-3 text-zinc-900 outline-none focus:border-violet-400 focus:ring-3 focus:ring-violet-100 ${focusRing}`}
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder="Ask for analysis, a chart, or a follow-up..."
        />
        <button
          className={`inline-grid h-11 w-11 place-items-center rounded-lg border-0 bg-violet-600 text-white hover:bg-violet-800 ${interactive}`}
          type="submit"
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}

function DataView({
  datasets,
  error,
  isUploading,
  onDelete,
  onImport,
  onRefresh,
  onUpload,
}: {
  datasets: Dataset[];
  error: string | null;
  isUploading: boolean;
  onDelete: (datasetId: number) => void;
  onImport: (datasetId: number) => void;
  onRefresh: () => void;
  onUpload: (file: File | null) => void;
}) {
  return (
    <section className="grid max-h-screen min-w-0 grid-rows-[auto_auto_auto_1fr] max-[820px]:min-h-[calc(100vh-300px)] max-[820px]:max-h-none">
      <header className={panelHeader}>
        <div>
          <h1 className={panelTitle}>Data</h1>
          <p className={panelSubtitle}>Upload local files, import staged files, or refresh Postgres tables.</p>
        </div>
        <button className={secondaryButton} onClick={onRefresh}>
          <RefreshCw size={17} />
          <span>Refresh Postgres</span>
        </button>
      </header>

      {error && <div className="mx-6 mt-3.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-rose-800">{error}</div>}

      <div className="flex items-center gap-3 px-6 pt-[18px] max-[560px]:px-3.5">
        <label className={uploadButton}>
          <FileUp size={18} />
          <span>{isUploading ? "Uploading..." : "Upload CSV/XLSX"}</span>
          <input
            className="hidden"
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={isUploading}
            onChange={(event) => {
              onUpload(event.target.files?.[0] ?? null);
              event.currentTarget.value = "";
            }}
          />
        </label>
        <span className="text-sm text-zinc-600">{datasets.length} uploaded/staged datasets</span>
      </div>

      <section className="grid content-start gap-2.5 overflow-auto p-6 max-[560px]:px-3.5" aria-label="Uploaded datasets">
        <div className="text-xs font-extrabold tracking-normal text-zinc-500 uppercase">Uploaded CSV files</div>
        {datasets.length === 0 && (
          <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-4 text-sm text-zinc-600">
            No uploaded CSV/XLSX files yet. Upload a file here and it will appear in this list.
          </div>
        )}
        {datasets.map((dataset) => (
          <div
            className="grid items-center gap-2.5 rounded-lg border border-zinc-200 bg-white p-3 max-[560px]:grid-cols-[20px_minmax(0,1fr)_30px] min-[561px]:grid-cols-[20px_minmax(0,1fr)_auto_30px]"
            key={dataset.id}
          >
            <Database className="text-violet-600" size={18} />
            <span className="min-w-0">
              <strong className="block overflow-hidden text-ellipsis whitespace-nowrap">{dataset.display_name}</strong>
              <small className="block overflow-hidden text-ellipsis whitespace-nowrap text-zinc-600">
                {dataset.row_count.toLocaleString()} rows - {dataset.is_imported ? `DB table ${dataset.table_name}` : "local file"}
              </small>
            </span>
            {!dataset.is_imported && (
              <button
                className={`min-h-[30px] whitespace-nowrap rounded-lg border border-violet-300 bg-violet-50 px-2.5 text-violet-800 hover:border-violet-600 hover:bg-violet-100 max-[560px]:col-[2/4] max-[560px]:w-full ${interactive}`}
                type="button"
                onClick={() => onImport(dataset.id)}
              >
                Save to DB
              </button>
            )}
            <button
              className={iconButton}
              type="button"
              aria-label={`Remove ${dataset.display_name}`}
              title="Remove dataset"
              onClick={() => onDelete(dataset.id)}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </section>
    </section>
  );
}

class ArtifactErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800">
          Chart rendering failed. The analysis is still available above.
        </div>
      );
    }
    return this.props.children;
  }
}

function ArtifactView(props: { artifact?: Artifact; artifactId: number }) {
  return (
    <ArtifactErrorBoundary>
      <ArtifactContent {...props} />
    </ArtifactErrorBoundary>
  );
}

function PlotlyFigure({ data, layout }: { data: Data[]; layout?: Partial<Layout> }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [renderError, setRenderError] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let cancelled = false;
    setRenderError(false);

    void Plotly.react(container, data, { ...(layout ?? {}), autosize: true }, { responsive: true }).catch(() => {
      if (!cancelled) {
        setRenderError(true);
      }
    });

    return () => {
      cancelled = true;
      Plotly.purge(container);
    };
  }, [data, layout]);

  if (renderError) {
    return (
      <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800">
        Chart rendering failed. The analysis is still available above.
      </div>
    );
  }

  return <div ref={containerRef} className="h-[360px] w-full" />;
}

function ArtifactContent({ artifact, artifactId }: { artifact?: Artifact; artifactId: number }) {
  if (!artifact) {
    return (
      <div className="mt-3 min-h-[300px] w-[min(820px,80vw)] overflow-hidden rounded-lg border border-zinc-200 bg-white max-[820px]:w-full max-[820px]:max-w-full">
        Loading artifact...
      </div>
    );
  }

  if (artifact.kind === "plotly" && artifact.payload) {
    const payload = artifact.payload as { data?: Data[]; layout?: Partial<Layout> };
    return (
      <div className="mt-3 min-h-[300px] w-[min(820px,80vw)] overflow-hidden rounded-lg border border-zinc-200 bg-white max-[820px]:w-full max-[820px]:max-w-full">
        <PlotlyFigure data={payload.data ?? []} layout={payload.layout} />
      </div>
    );
  }
  if (artifact.mime_type === "image/png") {
    return (
      <img
        className="mt-3 block max-w-[min(820px,80vw)] rounded-lg border border-zinc-200 max-[820px]:w-full max-[820px]:max-w-full"
        src={artifactUrl(artifactId)}
        alt={artifact.title}
      />
    );
  }
  return (
    <a className={`mt-3 inline-flex font-extrabold text-violet-800 ${focusRing}`} href={artifactUrl(artifactId)}>
      Download {artifact.title}
    </a>
  );
}

export default App;
