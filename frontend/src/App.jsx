import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_URL = "http://localhost:8000";

function App() {
  // ============================================================
  // AUTH STATE
  // ============================================================

  const [isLogin, setIsLogin] = useState(true);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [token, setToken] = useState(
    localStorage.getItem("access_token")
  );

  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // ============================================================
  // CHAT STATE
  // ============================================================

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ============================================================
  // UPLOAD STATE
  // ============================================================

  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  const fileInputRef = useRef(null);

  // ============================================================
  // LOGIN / REGISTER
  // ============================================================

  async function handleAuth(event) {
    event.preventDefault();

    setAuthError("");
    setAuthLoading(true);

    const endpoint = isLogin
      ? "/auth/login"
      : "/auth/register";

    try {
      const response = await fetch(
        `${API_URL}${endpoint}`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Authentication failed"
        );
      }

      if (isLogin) {
        localStorage.setItem(
          "access_token",
          data.access_token
        );

        setToken(data.access_token);
        setPassword("");
      } else {
        setIsLogin(true);

        setAuthError(
          "Registration successful. Please login."
        );

        setPassword("");
      }
    } catch (error) {
      setAuthError(error.message);
    } finally {
      setAuthLoading(false);
    }
  }

  // ============================================================
  // LOGOUT
  // ============================================================

  function logout() {
    localStorage.removeItem("access_token");

    setToken(null);

    setMessages([]);

    setConversationId(null);

    setUploadMessage("");
    setUploadError("");

    setSidebarOpen(false);
  }

  // ============================================================
  // PDF UPLOAD
  // ============================================================

  async function handleFileUpload(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setUploadMessage("");
    setUploadError("");

    if (file.type !== "application/pdf") {
      setUploadError(
        "Please select a PDF file."
      );

      event.target.value = "";

      return;
    }

    setUploading(true);

    setUploadMessage(
      `Uploading ${file.name}...`
    );

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API_URL}/documents/upload`,
        {
          method: "POST",

          headers: {
            Authorization: `Bearer ${token}`,
          },

          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          logout();

          throw new Error(
            "Session expired. Please login again."
          );
        }

        throw new Error(
          data.detail || "Upload failed."
        );
      }

      setUploadMessage(
        `✓ ${file.name} uploaded successfully. ${data.chunks_created || 0} chunks created.`
      );

      setUploadError("");
    } catch (error) {
      console.error(error);

      setUploadError(
        error.message ||
        "Could not upload the PDF."
      );

      setUploadMessage("");
    } finally {
      setUploading(false);

      event.target.value = "";
    }
  }

  // ============================================================
  // OPEN FILE SELECTOR
  // ============================================================

  function openFileSelector() {
    if (uploading) {
      return;
    }

    fileInputRef.current?.click();
  }

  // ============================================================
  // SEND MESSAGE
  // ============================================================

  async function sendMessage() {
    if (!message.trim()) {
      return;
    }

    if (!token) {
      return;
    }

    const userMessage = message.trim();

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: userMessage,
      },
    ]);

    setMessage("");

    setLoading(true);

    setMessages((previous) => [
      ...previous,
      {
        role: "assistant",
        content: "",
        sources: [],
      },
    ]);

    try {
      const response = await fetch(
        `${API_URL}/chat/stream`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },

          body: JSON.stringify({
            message: userMessage,
            conversation_id: conversationId,
          }),
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          logout();

          throw new Error(
            "Session expired. Please login again."
          );
        }

        throw new Error(
          `Request failed: ${response.status}`
        );
      }

      if (!response.body) {
        throw new Error(
          "Streaming is not supported."
        );
      }

      const reader =
        response.body.getReader();

      const decoder =
        new TextDecoder();

      let buffer = "";

      while (true) {
        const { value, done } =
          await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(
          value,
          { stream: true }
        );

        const events =
          buffer.split("\n\n");

        buffer = events.pop();

        for (const event of events) {
          processSSEEvent(event);
        }
      }

      if (buffer.trim()) {
        processSSEEvent(buffer);
      }
    } catch (error) {
      console.error(error);

      setMessages((previous) => {
        const updated = [...previous];

        const lastIndex =
          updated.length - 1;

        if (
          updated[lastIndex] &&
          updated[lastIndex].role === "assistant"
        ) {
          updated[lastIndex] = {
            ...updated[lastIndex],

            content:
              error.message ||
              "Sorry, something went wrong.",
          };
        }

        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  // ============================================================
  // PROCESS SSE EVENT
  // ============================================================

  function processSSEEvent(event) {
    const lines =
      event.split("\n");

    let eventType = "";

    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType =
          line
            .replace("event:", "")
            .trim();
      }

      if (line.startsWith("data:")) {
        dataLines.push(
          line.slice(5).trimStart()
        );
      }
    }

    const data =
      dataLines.join("\n");

    // ==========================================================
    // ANSWER
    // ==========================================================

    if (eventType === "answer") {
      setMessages((previous) => {
        const updated = [...previous];

        const lastIndex =
          updated.length - 1;

        if (
          updated[lastIndex] &&
          updated[lastIndex].role === "assistant"
        ) {
          updated[lastIndex] = {
            ...updated[lastIndex],

            content:
              updated[lastIndex].content +
              data +
              "\n",
          };
        }

        return updated;
      });
    }

    // ==========================================================
    // SOURCES
    // ==========================================================

    if (eventType === "sources") {
      try {
        const sources =
          JSON.parse(data);

        setMessages((previous) => {
          const updated = [...previous];

          const lastIndex =
            updated.length - 1;

          if (
            updated[lastIndex] &&
            updated[lastIndex].role === "assistant"
          ) {
            updated[lastIndex] = {
              ...updated[lastIndex],

              sources,
            };
          }

          return updated;
        });
      } catch (error) {
        console.error(
          "Could not parse sources:",
          error
        );
      }
    }

    // ==========================================================
    // CONVERSATION ID
    // ==========================================================

    if (eventType === "conversation") {
      setConversationId(
        Number(data)
      );
    }
  }

  // ============================================================
  // NEW CHAT
  // ============================================================

  function createNewChat() {
    setMessages([]);

    setConversationId(null);

    setUploadMessage("");

    setUploadError("");

    setSidebarOpen(false);
  }

  // ============================================================
  // ENTER KEY
  // ============================================================

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  }

  // ============================================================
  // LOGIN / REGISTER SCREEN
  // ============================================================

  if (!token) {
    return (
      <div className="min-h-screen bg-[#07090f] text-white flex items-center justify-center px-4 py-10 relative overflow-hidden">
        {/* Ambient background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-48 -left-48 w-[28rem] h-[28rem] rounded-full bg-blue-600/15 blur-[100px]" />
          <div className="absolute -bottom-48 -right-48 w-[28rem] h-[28rem] rounded-full bg-violet-600/12 blur-[100px]" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[40rem] h-[40rem] rounded-full bg-indigo-500/5 blur-[120px]" />
        </div>

        <div className="relative w-full max-w-[420px]">
          {/* Brand */}
          <div className="text-center mb-9">
            <div className="mx-auto mb-5 w-[3.25rem] h-[3.25rem] rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-xl shadow-blue-500/25 ring-1 ring-white/10">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
                <path d="M5 19l.75 2.25L8 22l-2.25.75L5 25l-.75-2.25L2 22l2.25-.75L5 19z" transform="translate(0 -2) scale(0.7)" />
              </svg>
            </div>
            <h1 className="text-[1.75rem] sm:text-[2rem] font-semibold tracking-tight text-white">
              AI Knowledge
            </h1>
            <p className="text-blue-400/90 text-sm font-medium mt-1 tracking-wide">
              Assistant
            </p>
            <p className="text-slate-500 text-[13px] mt-3 leading-relaxed">
              Ask questions. Understand your documents.
            </p>
          </div>

          {/* Auth card */}
          <div className="rounded-2xl border border-slate-800/90 bg-[#0e1219]/90 backdrop-blur-xl p-6 sm:p-8 shadow-2xl shadow-black/40">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-white tracking-tight">
                {isLogin ? "Welcome back" : "Create your account"}
              </h2>
              <p className="text-[13px] text-slate-500 mt-1.5 leading-relaxed">
                {isLogin
                  ? "Sign in to continue to your workspace."
                  : "Start building your personal knowledge base."}
              </p>
            </div>

            <form onSubmit={handleAuth} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-wider text-slate-500 mb-2">
                  Email address
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </span>
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    required
                    className="w-full rounded-xl bg-slate-900/70 border border-slate-700/70 pl-10 pr-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-blue-500/70 focus:ring-2 focus:ring-blue-500/15"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-wider text-slate-500 mb-2">
                  Password
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Enter your password"
                    required
                    className="w-full rounded-xl bg-slate-900/70 border border-slate-700/70 pl-10 pr-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-blue-500/70 focus:ring-2 focus:ring-blue-500/15"
                  />
                </div>
              </div>

              {/* Error / success message */}
              {authError && (
                <div className="rounded-xl bg-amber-500/10 border border-amber-500/25 px-3.5 py-2.5 text-[13px] text-amber-200 leading-relaxed">
                  {authError}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={authLoading}
                className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:from-blue-500 hover:to-violet-500 hover:shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-600 disabled:hover:to-violet-600"
              >
                {authLoading
                  ? "Please wait..."
                  : isLogin
                    ? "Sign in"
                    : "Create account"}
              </button>
            </form>

            {/* Switch mode */}
            <div className="mt-6 pt-5 border-t border-slate-800/80 text-center">
              <span className="text-[13px] text-slate-500">
                {isLogin
                  ? "Don't have an account? "
                  : "Already have an account? "}
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin);
                  setAuthError("");
                }}
                className="text-[13px] font-medium text-blue-400 hover:text-blue-300 transition"
              >
                {isLogin ? "Create one" : "Sign in"}
              </button>
            </div>
          </div>

          <p className="text-center text-[11px] text-slate-600 mt-6 tracking-wide">
            AI-powered document intelligence
          </p>
        </div>
      </div>
    );
  }

  // ============================================================
  // CHAT UI
  // ============================================================

  return (
    <div className="h-screen bg-[#07090f] text-white flex overflow-hidden">
      {/* ======================================================
          MOBILE OVERLAY
      ====================================================== */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-[2px] z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ======================================================
          SIDEBAR
      ====================================================== */}
      <aside
        className={`
          fixed md:relative z-40
          h-full w-[17.5rem]
          bg-[#0b0e14]
          border-r border-slate-800/70
          flex flex-col
          transition-transform duration-200 ease-out
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        {/* Brand */}
        <div className="flex items-center justify-between px-4 pt-5 pb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-md shadow-blue-500/20 ring-1 ring-white/10">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-sm text-white tracking-tight truncate">
                AI Knowledge
              </p>
              <p className="text-[11px] text-slate-500 truncate">
                Assistant
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="md:hidden shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:bg-slate-800/80 hover:text-slate-200 transition"
            aria-label="Close sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        {/* Actions */}
        <div className="px-3 space-y-2">
          {/* New conversation */}
          <button
            type="button"
            onClick={createNewChat}
            className="w-full flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-3.5 py-2.5 text-[13px] font-medium text-white shadow-md shadow-blue-600/15 transition hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/25"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            New conversation
          </button>

          {/* Upload PDF */}
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              type="button"
              onClick={openFileSelector}
              disabled={uploading}
              className="w-full flex items-center gap-2.5 rounded-xl border border-slate-800/90 bg-slate-900/40 px-3.5 py-2.5 text-[13px] text-slate-300 transition hover:bg-slate-800/60 hover:border-slate-700 hover:text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="animate-spin text-slate-400">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              )}
              {uploading ? "Uploading PDF..." : "Upload PDF"}
            </button>
          </div>

          {/* Upload status */}
          {uploadMessage && (
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3 py-2.5 text-[12px] text-emerald-300 leading-relaxed">
              {uploadMessage}
            </div>
          )}
          {uploadError && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-[12px] text-red-300 leading-relaxed">
              {uploadError}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="mx-4 my-4 border-t border-slate-800/70" />

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto px-3 min-h-0">
          <p className="text-[10px] uppercase tracking-[0.12em] font-semibold text-slate-600 px-1.5 mb-2.5">
            Conversations
          </p>

          {conversationId ? (
            <div className="rounded-xl bg-slate-800/50 border border-slate-700/40 px-3 py-2.5">
              <div className="flex items-center gap-2.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-40" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400" />
                </span>
                <span className="text-[13px] text-slate-200 truncate font-medium">
                  Conversation #{conversationId}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-1 ml-[18px]">
                Current conversation
              </p>
            </div>
          ) : (
            <div className="px-1.5 py-3 text-[12px] text-slate-600">
              No conversations yet
            </div>
          )}
        </div>

        {/* User / Logout */}
        <div className="border-t border-slate-800/70 px-3 py-3 mt-auto">
          <div className="flex items-center gap-2.5 px-1.5 mb-2.5">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700/60 flex items-center justify-center text-[11px] font-semibold text-slate-400">
              AI
            </div>
            <div className="min-w-0">
              <p className="text-[13px] text-slate-300 truncate font-medium">
                Knowledge Workspace
              </p>
              <p className="text-[11px] text-slate-600">
                Signed in
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="w-full flex items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] text-slate-500 hover:bg-slate-800/70 hover:text-slate-200 transition"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* ======================================================
          MAIN
      ====================================================== */}
      <main className="flex-1 min-w-0 flex flex-col bg-[#07090f]">
        {/* ====================================================
            HEADER
        ==================================================== */}
        <header className="h-14 shrink-0 border-b border-slate-800/60 bg-[#0b0e14]/80 backdrop-blur-xl px-3 sm:px-5 flex items-center gap-3">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="md:hidden shrink-0 w-9 h-9 rounded-lg border border-slate-800 bg-slate-900/60 flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Open sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5">
              <h2 className="font-semibold text-sm sm:text-[15px] text-white tracking-tight truncate">
                AI Knowledge Assistant
              </h2>
              <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Online
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 truncate">
              Ask questions about your uploaded documents
            </p>
          </div>
        </header>

        {/* ====================================================
            MESSAGES
        ==================================================== */}
        <section className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
            {/* Empty state */}
            {messages.length === 0 && (
              <div className="min-h-[calc(100vh-14rem)] flex items-center justify-center">
                <div className="text-center max-w-lg w-full">
                  <div className="mx-auto mb-6 w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500/15 to-violet-500/15 border border-blue-500/20 flex items-center justify-center shadow-lg shadow-blue-500/5">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400">
                      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
                    </svg>
                  </div>
                  <h3 className="text-2xl sm:text-[1.75rem] font-semibold tracking-tight text-white">
                    How can I help you?
                  </h3>
                  <p className="text-[14px] text-slate-500 mt-3 leading-relaxed max-w-md mx-auto">
                    Upload a PDF and ask questions about its content. I’ll search your documents and give you a clear answer.
                  </p>

                  <div className="grid sm:grid-cols-2 gap-3 mt-8 text-left">
                    <button
                      type="button"
                      onClick={() => setMessage("Summarize this document")}
                      className="group rounded-xl border border-slate-800/90 bg-[#0e1219]/80 p-4 text-left transition hover:border-slate-700 hover:bg-slate-900/60"
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500 group-hover:text-blue-400 transition">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                          <line x1="16" y1="13" x2="8" y2="13" />
                          <line x1="16" y1="17" x2="8" y2="17" />
                          <polyline points="10 9 9 9 8 9" />
                        </svg>
                        <p className="text-[13px] font-medium text-slate-300 group-hover:text-white transition">
                          Summarize a document
                        </p>
                      </div>
                      <p className="text-[12px] text-slate-600 leading-relaxed">
                        Get the main ideas quickly
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setMessage("What are the key concepts in this document?")}
                      className="group rounded-xl border border-slate-800/90 bg-[#0e1219]/80 p-4 text-left transition hover:border-slate-700 hover:bg-slate-900/60"
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500 group-hover:text-blue-400 transition">
                          <circle cx="12" cy="12" r="10" />
                          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                          <line x1="12" y1="17" x2="12.01" y2="17" />
                        </svg>
                        <p className="text-[13px] font-medium text-slate-300 group-hover:text-white transition">
                          Find key concepts
                        </p>
                      </div>
                      <p className="text-[12px] text-slate-600 leading-relaxed">
                        Discover the important topics
                      </p>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Messages list */}
            <div className="space-y-7">
              {messages.map((item, index) => {
                const isUser = item.role === "user";
                const isLast = index === messages.length - 1;

                return (
                  <div
                    key={index}
                    className={isUser ? "flex justify-end" : "flex justify-start"}
                  >
                    <div
                      className={
                        isUser
                          ? "max-w-[85%] sm:max-w-[75%]"
                          : "w-full max-w-3xl"
                      }
                    >
                      {isUser ? (
                        /* User bubble */
                        <div className="flex justify-end">
                          <div className="rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5 text-[14px] leading-relaxed text-white shadow-lg shadow-blue-600/10">
                            {item.content}
                          </div>
                        </div>
                      ) : (
                        /* Assistant message */
                        <div className="flex gap-3">
                          <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mt-0.5 shadow-md shadow-blue-500/15 ring-1 ring-white/10">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                              <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z" />
                            </svg>
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="text-[13px] font-semibold text-slate-200">
                                Assistant
                              </span>
                              {isLast && loading && (
                                <span className="inline-flex items-center gap-1.5 text-[11px] text-blue-400 font-medium">
                                  <span className="relative flex h-1.5 w-1.5">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-50" />
                                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-400" />
                                  </span>
                                  Generating
                                </span>
                              )}
                            </div>

                            {/* Answer content */}
                            <div className="text-[14px] sm:text-[15px] leading-7 text-slate-300 break-words">
                              {item.content && (
                                <ReactMarkdown
                                  components={{
                                    p: ({ children }) => (
                                      <p className="mb-3 last:mb-0">
                                        {children}
                                      </p>
                                    ),
                                    strong: ({ children }) => (
                                      <strong className="font-semibold text-white">
                                        {children}
                                      </strong>
                                    ),
                                    em: ({ children }) => (
                                      <em className="italic text-slate-200">
                                        {children}
                                      </em>
                                    ),
                                    h1: ({ children }) => (
                                      <h1 className="text-xl font-bold text-white mb-3 mt-1">
                                        {children}
                                      </h1>
                                    ),
                                    h2: ({ children }) => (
                                      <h2 className="text-lg font-bold text-white mb-2.5 mt-5">
                                        {children}
                                      </h2>
                                    ),
                                    h3: ({ children }) => (
                                      <h3 className="text-base font-semibold text-white mb-2 mt-4">
                                        {children}
                                      </h3>
                                    ),
                                    ul: ({ children }) => (
                                      <ul className="list-disc pl-5 mb-3 space-y-1.5 marker:text-slate-500">
                                        {children}
                                      </ul>
                                    ),
                                    ol: ({ children }) => (
                                      <ol className="list-decimal pl-5 mb-3 space-y-1.5 marker:text-slate-500">
                                        {children}
                                      </ol>
                                    ),
                                    li: ({ children }) => (
                                      <li className="pl-0.5">
                                        {children}
                                      </li>
                                    ),
                                    a: ({ href, children }) => (
                                      <a
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-400 underline underline-offset-2 hover:text-blue-300 transition"
                                      >
                                        {children}
                                      </a>
                                    ),
                                    blockquote: ({ children }) => (
                                      <blockquote className="border-l-2 border-slate-600 pl-4 my-3 text-slate-400 italic">
                                        {children}
                                      </blockquote>
                                    ),
                                    code: ({ className, children }) => {
                                      const isBlock = className?.includes("language-");
                                      if (isBlock) {
                                        return (
                                          <code className="block rounded-lg bg-slate-900/90 border border-slate-800 px-3.5 py-3 text-[13px] text-slate-200 font-mono overflow-x-auto my-3">
                                            {children}
                                          </code>
                                        );
                                      }
                                      return (
                                        <code className="rounded-md bg-slate-800/90 px-1.5 py-0.5 text-[13px] text-blue-300 font-mono">
                                          {children}
                                        </code>
                                      );
                                    },
                                    pre: ({ children }) => (
                                      <pre className="my-3 overflow-x-auto">
                                        {children}
                                      </pre>
                                    ),
                                  }}
                                >
                                  {item.content}
                                </ReactMarkdown>
                              )}

                              {loading && isLast && !item.content && (
                                <span className="inline-flex gap-1.5 align-middle mt-1">
                                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                                </span>
                              )}
                            </div>

                            {/* Sources */}
                            {item.sources && item.sources.length > 0 && (
                              <div className="mt-5">
                                <div className="flex items-center gap-2 mb-2.5">
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                  </svg>
                                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                                    Sources
                                  </span>
                                  <span className="text-[10px] rounded-full bg-slate-800/80 px-1.5 py-0.5 text-slate-500 font-medium">
                                    {item.sources.length}
                                  </span>
                                </div>

                                <div className="grid gap-2">
                                  {item.sources.map((source, sourceIndex) => (
                                    <div
                                      key={sourceIndex}
                                      className="rounded-xl border border-slate-800/80 bg-[#0e1219]/70 p-3 transition hover:border-slate-700/80 hover:bg-slate-900/40"
                                    >
                                      <div className="flex items-start gap-3">
                                        <div className="shrink-0 w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/15 flex items-center justify-center">
                                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                            <polyline points="14 2 14 8 20 8" />
                                          </svg>
                                        </div>
                                        <div className="min-w-0 flex-1">
                                          <p className="text-[12px] font-medium text-slate-300 break-words leading-snug">
                                            {source.filename ||
                                              source.source ||
                                              `Document #${source.document_id}`}
                                          </p>
                                          <div className="flex flex-wrap gap-1.5 mt-1.5">
                                            {source.page_number && (
                                              <span className="text-[10px] text-slate-500 bg-slate-800/70 rounded-md px-1.5 py-0.5">
                                                Page {source.page_number}
                                              </span>
                                            )}
                                            {source.section && (
                                              <span className="text-[10px] text-slate-500 bg-slate-800/70 rounded-md px-1.5 py-0.5">
                                                {source.section}
                                              </span>
                                            )}
                                            {source.chunk_type && (
                                              <span className="text-[10px] text-slate-600 bg-slate-800/50 rounded-md px-1.5 py-0.5">
                                                {source.chunk_type}
                                              </span>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ====================================================
            INPUT AREA
        ==================================================== */}
        <div className="shrink-0 border-t border-slate-800/60 bg-[#0b0e14]/90 backdrop-blur-xl px-3 sm:px-5 py-3 sm:py-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end gap-2 rounded-2xl border border-slate-800/90 bg-[#0e1219] p-1.5 shadow-inner focus-within:border-slate-700 transition">
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                rows={1}
                placeholder="Ask something about your documents..."
                className="flex-1 resize-none bg-transparent px-3.5 py-2.5 text-[14px] text-slate-200 placeholder:text-slate-600 outline-none max-h-32 disabled:opacity-50 leading-relaxed"
              />
              <button
                type="button"
                onClick={sendMessage}
                disabled={loading || !message.trim()}
                className="shrink-0 w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white transition hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed shadow-md shadow-blue-600/15"
                title="Send message"
              >
                {loading ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="animate-spin">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5" />
                    <polyline points="5 12 12 5 19 12" />
                  </svg>
                )}
              </button>
            </div>
            <p className="text-center text-[10px] text-slate-600 mt-2.5 tracking-wide">
              Enter to send · Shift + Enter for a new line
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;