import { useRef, useState } from "react";

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

      // Login returns JWT
      if (isLogin) {
        localStorage.setItem(
          "access_token",
          data.access_token
        );

        setToken(data.access_token);

        setPassword("");
      } else {
        // Registration successful
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
  }


  // ============================================================
  // PDF UPLOAD
  // ============================================================

  async function handleFileUpload(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    // Clear previous messages
    setUploadMessage("");
    setUploadError("");

    // Only PDF files
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
        `✅ ${file.name} uploaded successfully. ${data.chunks_created || 0} chunks created.`
      );

      setUploadError("");

    } catch (error) {
      console.error(error);

      setUploadError(
        error.message || "Could not upload the PDF."
      );

      setUploadMessage("");

    } finally {
      setUploading(false);

      // Allow selecting the same file again
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

    const userMessage = message;

    // Show user message
    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: userMessage,
      },
    ]);

    setMessage("");

    setLoading(true);

    // Create empty assistant message
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

      // ========================================================
      // READ SSE STREAM
      // ========================================================

      const reader = response.body.getReader();

      const decoder = new TextDecoder();

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

      // Process remaining event
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
    let data = "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType =
          line
            .replace("event:", "")
            .trim();
      }

      if (line.startsWith("data:")) {
        // IMPORTANT:
        // Do not trim SSE answer chunks.
        // Spaces are part of the streamed text.
        data += line.slice(5);
      }
    }


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
              data,
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
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">

        <div className="w-full max-w-md">

          {/* Logo */}

          <div className="text-center mb-8">

            <div className="text-5xl mb-4">
              🤖
            </div>

            <h1 className="text-3xl font-bold">
              AI Knowledge Assistant
            </h1>

            <p className="text-slate-400 mt-2">
              Your intelligent document assistant
            </p>

          </div>


          {/* Card */}

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">

            <h2 className="text-xl font-semibold mb-6">
              {isLogin
                ? "Welcome back"
                : "Create account"}
            </h2>


            <form
              onSubmit={handleAuth}
              className="space-y-4"
            >

              {/* Email */}

              <div>

                <label className="block text-sm text-slate-400 mb-2">
                  Email
                </label>

                <input
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="Enter your email"
                  required
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 outline-none focus:border-blue-500"
                />

              </div>


              {/* Password */}

              <div>

                <label className="block text-sm text-slate-400 mb-2">
                  Password
                </label>

                <input
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="Enter your password"
                  required
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 outline-none focus:border-blue-500"
                />

              </div>


              {/* Error / message */}

              {authError && (
                <div className="rounded-lg bg-slate-800 border border-slate-700 p-3 text-sm text-yellow-400">
                  {authError}
                </div>
              )}


              {/* Submit */}

              <button
                type="submit"
                disabled={authLoading}
                className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {authLoading
                  ? "Please wait..."
                  : isLogin
                    ? "Login"
                    : "Create Account"}
              </button>

            </form>


            {/* Switch */}

            <div className="text-center mt-6">

              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  setAuthError("");
                }}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                {isLogin
                  ? "Don't have an account? Create one"
                  : "Already have an account? Login"}
              </button>

            </div>

          </div>

        </div>

      </div>
    );
  }


  // ============================================================
  // CHAT UI
  // ============================================================

  return (
    <div className="min-h-screen bg-slate-950 text-white flex">

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col">

        <h1 className="text-xl font-bold mb-6">
          🤖 AI Knowledge
        </h1>


        {/* New Chat */}

        <button
          onClick={createNewChat}
          className="w-full rounded-lg bg-blue-600 px-4 py-3 text-left hover:bg-blue-700"
        >
          + New Chat
        </button>


        {/* ==================================================
            UPLOAD PDF
        ================================================== */}

        <div className="mt-4">

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            onChange={handleFileUpload}
            className="hidden"
          />

          <button
            onClick={openFileSelector}
            disabled={uploading}
            className="w-full rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 text-left hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading
              ? "⏳ Uploading..."
              : "📄 Upload PDF"}
          </button>

        </div>


        {/* Upload status */}

        {uploadMessage && (
          <div className="mt-3 rounded-lg bg-green-950 border border-green-800 p-3 text-xs text-green-300">
            {uploadMessage}
          </div>
        )}

        {uploadError && (
          <div className="mt-3 rounded-lg bg-red-950 border border-red-800 p-3 text-xs text-red-300">
            {uploadError}
          </div>
        )}


        {/* Conversations */}

        <div className="mt-6">

          <p className="text-sm text-slate-400 mb-3">
            Conversations
          </p>

          {conversationId && (
            <div className="rounded-lg bg-slate-800 p-3 text-sm">
              Conversation #{conversationId}
            </div>
          )}

        </div>


        {/* Logout */}

        <button
          onClick={logout}
          className="mt-auto text-left text-sm text-slate-400 hover:text-white"
        >
          Logout
        </button>

      </aside>


      {/* ======================================================
          MAIN CHAT
      ====================================================== */}

      <main className="flex-1 flex flex-col">


        {/* Header */}

        <header className="border-b border-slate-800 p-4">

          <h2 className="text-lg font-semibold">
            AI Knowledge Assistant
          </h2>

          <p className="text-sm text-slate-400">
            Ask questions about your documents
          </p>

        </header>


        {/* Messages */}

        <section className="flex-1 overflow-y-auto p-6">

          <div className="max-w-3xl mx-auto space-y-6">

            {messages.length === 0 && (
              <div className="text-center mt-20">

                <div className="text-5xl mb-4">
                  🤖
                </div>

                <h3 className="text-2xl font-bold">
                  Welcome to AI Knowledge Assistant
                </h3>

                <p className="text-slate-400 mt-2">
                  Upload a PDF and ask questions about it.
                </p>

              </div>
            )}


            {messages.map((item, index) => (

              <div
                key={index}
                className={
                  item.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >

                <div
                  className={
                    item.role === "user"
                      ? "bg-blue-600 rounded-2xl px-4 py-3 max-w-xl"
                      : "bg-slate-800 rounded-2xl px-4 py-3 max-w-xl"
                  }
                >

                  {item.role === "assistant" && (
                    <p className="font-semibold mb-2">
                      🤖 Assistant
                    </p>
                  )}


                  <p className="whitespace-pre-wrap">

                    {item.content}

                    {loading &&
                      index === messages.length - 1 &&
                      item.role === "assistant" && (
                        <span className="animate-pulse">
                          ▌
                        </span>
                      )}

                  </p>


                  {/* ==================================================
                      SOURCES + METADATA
                  ================================================== */}

                  {item.role === "assistant" &&
                    item.sources &&
                    item.sources.length > 0 && (

                    <div className="mt-4 border-t border-slate-700 pt-3">

                      <p className="text-xs text-slate-400 mb-2">
                        📚 Sources
                      </p>


                      {item.sources.map(
                        (source, sourceIndex) => (

                        <div
                          key={sourceIndex}
                          className="mb-3 rounded-lg bg-slate-900 p-3 text-xs text-slate-400"
                        >

                          <p className="text-slate-300 font-medium">
                            📄{" "}
                            {source.filename ||
                              source.source ||
                              `Document #${source.document_id}`}
                          </p>

                          {source.page_number && (
                            <p className="mt-1">
                              📖 Page {source.page_number}
                            </p>
                          )}

                          {source.section && (
                            <p className="mt-1">
                              📑 {source.section}
                            </p>
                          )}

                          {source.chunk_type && (
                            <p className="mt-1">
                              🏷️ {source.chunk_type}
                            </p>
                          )}

                          {!source.filename &&
                            !source.source &&
                            (
                              <p className="mt-1">
                                Document #
                                {source.document_id}
                                {" · "}
                                Chunk #
                                {source.chunk_id}
                              </p>
                            )}

                        </div>

                      ))}

                    </div>

                  )}

                </div>

              </div>

            ))}

          </div>

        </section>


        {/* ======================================================
            INPUT
        ====================================================== */}

        <div className="border-t border-slate-800 p-4">

          <div className="max-w-3xl mx-auto flex gap-3">

            <input
              type="text"
              value={message}
              onChange={(event) =>
                setMessage(event.target.value)
              }
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="Ask something about your documents..."
              className="flex-1 rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 outline-none focus:border-blue-500 disabled:opacity-50"
            />


            <button
              onClick={sendMessage}
              disabled={
                loading ||
                !message.trim()
              }
              className="rounded-xl bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? "Thinking..."
                : "Send"}
            </button>

          </div>

        </div>

      </main>

    </div>
  );
}

export default App;