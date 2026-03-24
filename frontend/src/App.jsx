import { useState, useRef, useEffect, useCallback } from "react";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const SESSION_ID = "s_" + Math.random().toString(36).slice(2, 10);

const SOURCES = [
  { id: 1, title: "GitLab Handbook",      url: "https://handbook.gitlab.com/",                        tag: "Culture",    indexed: true },
  { id: 2, title: "Product Direction",    url: "https://about.gitlab.com/direction/",                tag: "Strategy",   indexed: true },
  { id: 3, title: "CI/CD YAML Reference", url: "https://docs.gitlab.com/ee/ci/yaml/",               tag: "CI/CD",      indexed: true },
  { id: 4, title: "GitLab API",           url: "https://docs.gitlab.com/ee/api/",                   tag: "API",        indexed: true },
  { id: 5, title: "GitLab Runner",        url: "https://docs.gitlab.com/runner/",                   tag: "Runner",     indexed: true },
  { id: 6, title: "Package Registry",     url: "https://docs.gitlab.com/ee/user/packages/",         tag: "Packages",   indexed: true },
  { id: 7, title: "K8s Agent",            url: "https://docs.gitlab.com/ee/user/clusters/agent/",   tag: "Kubernetes", indexed: true },
  { id: 8, title: "Infrastructure as Code", url: "https://docs.gitlab.com/ee/user/infrastructure/iac/", tag: "IaC",    indexed: true },
];

const ACTIONS = [
  { label: "Fix: Executor Not Found", prompt: "My GitLab pipeline fails with \"executor docker not found\". How do I fix this?" },
  { label: "Protect Branch via API", prompt: "How do I protect a branch via the GitLab API to prevent direct pushes?" },
  { label: "K8s Agent Setup",       prompt: "How do I configure the GitLab Agent for Kubernetes?" },
  { label: "Manual Pipeline Trigger", prompt: "How do I trigger a GitLab pipeline manually?" },
  { label: "Remote Work",           prompt: "How does GitLab approach remote work and async communication?" },
  { label: "What is GitLab?",        prompt: "What is GitLab and what are its main features?" },
];

const CI_LANGUAGES = [
  { value: "Python",  testDefault: "pytest" },
  { value: "Node.js", testDefault: "jest" },
  { value: "Go",      testDefault: "go test" },
  { value: "Java",    testDefault: "JUnit" },
  { value: "Ruby",    testDefault: "RSpec" },
  { value: "Rust",    testDefault: "cargo test" },
  { value: "PHP",     testDefault: "PHPUnit" },
  { value: ".NET",    testDefault: "xUnit" },
];
const CI_BUILD_OPTIONS = ["Docker", "Kaniko", "Buildpacks", "None"];
const CI_DEPLOY_OPTIONS = ["AWS ECS", "AWS Lambda", "GKE", "Azure App Service", "DigitalOcean", "Kubernetes (generic)", "Fly.io", "None"];

const DEMOS = {
  "core values": "GitLab's six **CREDIT** values:\n\n**Collaboration** — Help teammates across all roles [Source 1].\n**Results** — Deliver on commitments to customers and users [Source 1].\n**Efficiency** — Work on the right things, nothing more [Source 1].\n**Diversity, Inclusion & Belonging** — Make a positive impact on the world [Source 1].\n**Iteration** — Ship the smallest thing, then improve [Source 1].\n**Transparency** — Be open, even when uncomfortable [Source 1].",
  "remote work":  "GitLab is fully **all-remote** with team members in 65+ countries [Source 2].\n\n- **Async-first** — communicate across timezones by default [Source 2]\n- **Write everything down** — if it's not documented, it doesn't exist [Source 2]\n- **Results over hours** — output is measured, not time [Source 2]",
};

// ── API ───────────────────────────────────────────────────────────────────────
async function apiChat(query) {
  const r = await fetch(`${API_BASE}/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: SESSION_ID }),
  });
  if (!r.ok) throw new Error(r.status);
  return r.json();
}
async function apiIngest() {
  const r = await fetch(`${API_BASE}/ingest`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_reingest: false }),
  });
  return r.json();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function Markdown({ text }) {
  const html = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, `<code style="font-family:'JetBrains Mono',monospace;font-size:11.5px;background:#f4f4f5;padding:1px 5px;border-radius:3px;border:1px solid #e4e4e7;color:#52525b">$1</code>`)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, `<a href="$2" target="_blank" rel="noopener" style="color:#0ea5e9;text-decoration:underline">$1</a>`)
    .replace(/\n/g, "<br/>");
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function Spinner({ color = "#0ea5e9", size = 13 }) {
  return (
    <span style={{
      width: size, height: size, display: "inline-block", borderRadius: "50%",
      border: `2px solid #e4e4e7`, borderTopColor: color,
      animation: "spin .7s linear infinite",
    }} />
  );
}

function TypingDots() {
  return (
    <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: "50%", background: "#0ea5e9",
          display: "inline-block",
          animation: "blink 1.2s ease infinite",
          animationDelay: `${i * 0.16}s`,
        }} />
      ))}
    </span>
  );
}

// ── CI/CD Generator ──────────────────────────────────────────────────────────
const selectStyle = {
  width: "100%", padding: "6px 8px", fontSize: 12, fontFamily: "inherit",
  border: "1px solid #e4e4e7", borderRadius: 5, background: "#fff", color: "#111",
  cursor: "pointer", outline: "none",
};

function CICDGenerator({ onGenerate, disabled }) {
  const [lang, setLang] = useState(CI_LANGUAGES[0].value);
  const [test, setTest] = useState(CI_LANGUAGES[0].testDefault);
  const [build, setBuild] = useState(CI_BUILD_OPTIONS[0]);
  const [deploy, setDeploy] = useState(CI_DEPLOY_OPTIONS[0]);
  const [open, setOpen] = useState(false);

  const handleLangChange = (v) => {
    setLang(v);
    const match = CI_LANGUAGES.find(l => l.value === v);
    if (match) setTest(match.testDefault);
  };

  const generate = () => {
    const parts = [`${lang} project`, test];
    if (build !== "None") parts.push(`${build} build`);
    if (deploy !== "None") parts.push(`deploy to ${deploy}`);
    onGenerate(`Create a GitLab CI/CD pipeline (.gitlab-ci.yml) for:\n${parts.map(p => `- ${p}`).join("\n")}`);
  };

  return (
    <div style={{ background: "#fff", border: "1px solid #e4e4e7", borderRadius: 6, overflow: "hidden" }}>
      <button onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", padding: "8px 11px", display: "flex", alignItems: "center", justifyContent: "space-between",
          background: open ? "#f9fafb" : "#fff", border: "none", cursor: "pointer",
          fontSize: 12.5, fontWeight: 500, color: "#111", fontFamily: "inherit", transition: "background .12s",
        }}>
        <span>CI/CD Generator</span>
        <span style={{ fontSize: 10, color: "#a1a1aa", transition: "transform .15s", transform: open ? "rotate(180deg)" : "none" }}>▼</span>
      </button>
      {open && (
        <div style={{ padding: "8px 11px 11px", borderTop: "1px solid #e4e4e7", display: "flex", flexDirection: "column", gap: 8 }}>
          <div>
            <div style={{ fontSize: 10, color: "#a1a1aa", marginBottom: 3, fontWeight: 500 }}>Language</div>
            <select value={lang} onChange={e => handleLangChange(e.target.value)} style={selectStyle}>
              {CI_LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.value}</option>)}
            </select>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#a1a1aa", marginBottom: 3, fontWeight: 500 }}>Test Framework</div>
            <input value={test} onChange={e => setTest(e.target.value)}
              style={{ ...selectStyle, cursor: "text" }} placeholder="e.g. pytest, jest" />
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#a1a1aa", marginBottom: 3, fontWeight: 500 }}>Build</div>
            <select value={build} onChange={e => setBuild(e.target.value)} style={selectStyle}>
              {CI_BUILD_OPTIONS.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "#a1a1aa", marginBottom: 3, fontWeight: 500 }}>Deploy Target</div>
            <select value={deploy} onChange={e => setDeploy(e.target.value)} style={selectStyle}>
              {CI_DEPLOY_OPTIONS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <button onClick={generate} disabled={disabled}
            style={{
              width: "100%", padding: "7px 12px", borderRadius: 5, border: "none",
              fontSize: 12, fontWeight: 500, fontFamily: "inherit", cursor: disabled ? "not-allowed" : "pointer",
              background: disabled ? "#e4e4e7" : "#111", color: disabled ? "#a1a1aa" : "#fff",
              transition: "all .15s", marginTop: 2,
            }}>
            Generate Pipeline
          </button>
        </div>
      )}
    </div>
  );
}

// ── Message ───────────────────────────────────────────────────────────────────
function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: isUser ? "flex-end" : "flex-start",
      marginBottom: 20,
      animation: msg.isNew ? "fadeUp .22s ease forwards" : "none",
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, letterSpacing: ".08em",
        textTransform: "uppercase", marginBottom: 5,
        color: isUser ? "#f59e0b" : "#a1a1aa",
      }}>
        {isUser ? "You" : "Assistant"}
      </div>
      <div style={{
        maxWidth: "85%", padding: "11px 14px", fontSize: 13.5, lineHeight: 1.65,
        borderRadius: isUser ? "10px 10px 2px 10px" : "2px 10px 10px 10px",
        background: isUser ? "#111" : "#f4f4f5",
        color: isUser ? "#fff" : "#111",
        border: isUser ? "none" : "1px solid #e4e4e7",
      }}>
        {msg.isLoading ? <TypingDots /> : <Markdown text={msg.text} />}
      </div>

      {msg.sources?.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6, maxWidth: "85%" }}>
          {msg.sources.map((src, i) => (
            <a key={i} href={src.url} target="_blank" rel="noopener"
              style={{
                fontSize: 11, fontWeight: 500, color: "#0ea5e9",
                background: "#f0f9ff", border: "1px solid #bae6fd",
                padding: "2px 8px", borderRadius: 4, textDecoration: "none", transition: "background .12s",
              }}
              onMouseOver={e => e.currentTarget.style.background = "#bae6fd"}
              onMouseOut={e => e.currentTarget.style.background = "#f0f9ff"}
            >
              {src.section || src.title}
            </a>
          ))}
        </div>
      )}

    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages] = useState([{
    id: "welcome", role: "bot", isNew: false, sources: [],
    text: "Hello! Ask me anything about GitLab's handbook, values, engineering practices, or product direction.",
  }]);
  const [input, setInput]             = useState("");
  const [busy, setBusy]               = useState(false);
  const [leftOpen, setLeftOpen]       = useState(true);
  const [rightOpen, setRightOpen]     = useState(true);
  const [ingestStatus, setIngest]     = useState("idle");
  const [apiConnected, setApi]        = useState(null);
  const [focused, setFocused]         = useState(false);
  const msgsRef  = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2500) })
      .then(() => setApi(true)).catch(() => setApi(false));
  }, []);

  useEffect(() => {
    msgsRef.current?.scrollTo({ top: msgsRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(async (override) => {
    const q = override ?? input.trim();
    if (!q || busy) return;
    setInput("");
    setMessages(prev => [...prev,
      { id: Date.now(),    role: "user", text: q, sources: [], isNew: true },
      { id: "loading",     role: "bot",  text: "", sources: [], isNew: true, isLoading: true },
    ]);
    setBusy(true);
    try {
      let resp;
      if (apiConnected) {
        resp = await apiChat(q);
      } else {
        await new Promise(r => setTimeout(r, 1200));
        const key = Object.keys(DEMOS).find(k => q.toLowerCase().includes(k));
        resp = {
          answer: key ? DEMOS[key] : `**Demo mode** — backend not connected at \`${API_BASE}\`.\n\nYour question: *"${q}"*\n\nConnect FastAPI to get real RAG-powered answers.`,
          sources: [
            { title: "GitLab Values", url: "https://handbook.gitlab.com/handbook/values/",                      section: "Culture" },
            { title: "Remote Work",   url: "https://handbook.gitlab.com/handbook/company/culture/all-remote/", section: "Remote"  },
          ],
          query_id: "demo_" + Date.now(),
        };
      }
      setMessages(prev => prev.filter(m => m.id !== "loading").concat({
        id: Date.now() + 1, role: "bot", isNew: true,
        text: resp.answer, sources: resp.sources || [], queryId: resp.query_id,
      }));
    } catch {
      setMessages(prev => prev.filter(m => m.id !== "loading").concat({
        id: Date.now() + 1, role: "bot", isNew: true, sources: [],
        text: `Couldn't reach the backend. Is the API running at \`${API_BASE}\`?`,
      }));
    } finally {
      setBusy(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [input, busy, apiConnected]);

  const handleIngest = async () => {
    setIngest("running");
    try { if (apiConnected) await apiIngest(); else await new Promise(r => setTimeout(r, 2000)); setIngest("done"); setTimeout(() => setIngest("idle"), 2500); }
    catch { setIngest("idle"); }
  };

  const indexed = SOURCES.filter(s => s.indexed).length;
  const canSend = input.trim() && !busy;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
        *{margin:0;padding:0;box-sizing:border-box}
        html,body,#root{height:100%}
        body{font-family:'Inter',system-ui,sans-serif;background:#fafafa;color:#111;-webkit-font-smoothing:antialiased}
        ::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:#d1d1d6;border-radius:3px}
        textarea:focus{outline:none} button:focus-visible{outline:2px solid #0ea5e9;outline-offset:2px}
        @keyframes blink{0%,60%,100%{opacity:.15}30%{opacity:1}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
        @keyframes spin{to{transform:rotate(360deg)}}
      `}</style>

      <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "#fafafa" }}>

        {/* HEADER */}
        <header style={{ height: 50, display: "flex", alignItems: "center", padding: "0 16px", gap: 10, background: "#fff", borderBottom: "1px solid #e4e4e7", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <rect width="22" height="22" rx="5" fill="#111"/>
              <path d="M11 4.5L16.5 17.5H5.5L11 4.5Z" fill="#f59e0b" opacity=".9"/>
              <path d="M11 8.5L13.8 17.5H8.2L11 8.5Z" fill="white" opacity=".95"/>
            </svg>
            <span style={{ fontSize: 14, fontWeight: 600 }}>GitLab Knowledge</span>
          </div>
          <div style={{ width: 1, height: 16, background: "#e4e4e7" }} />
          <span style={{ fontSize: 12, color: "#a1a1aa" }}>{indexed} of {SOURCES.length} sources indexed</span>
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 500, color: apiConnected === null ? "#a1a1aa" : apiConnected ? "#22c55e" : "#f59e0b" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: apiConnected === null ? "#d1d1d6" : apiConnected ? "#22c55e" : "#f59e0b" }} />
            {apiConnected === null ? "Checking" : apiConnected ? "API Connected" : "Demo Mode"}
          </div>
          <div style={{ display: "flex", gap: 4, marginLeft: 8 }}>
            {[["left", "⊞", leftOpen, setLeftOpen], ["right", "⊟", rightOpen, setRightOpen]].map(([k, icon, open, set]) => (
              <button key={k} onClick={() => set(p => !p)}
                style={{ width: 28, height: 28, border: "1px solid #e4e4e7", borderRadius: 5, cursor: "pointer", fontSize: 12, color: "#71717a", background: open ? "#f4f4f5" : "#fff", transition: "background .15s" }}>
                {icon}
              </button>
            ))}
          </div>
        </header>

        {/* BODY */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

          {/* LEFT */}
          <div style={{ width: leftOpen ? 252 : 0, minWidth: leftOpen ? 252 : 0, overflow: "hidden", transition: "all .2s ease", borderRight: "1px solid #e4e4e7", background: "#fff", display: "flex", flexDirection: "column", flexShrink: 0 }}>
            <div style={{ padding: 14, flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#a1a1aa", marginBottom: 8 }}>Sources</div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ height: 2, background: "#e4e4e7", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ height: "100%", borderRadius: 2, background: "linear-gradient(90deg,#f59e0b,#0ea5e9)", width: `${(indexed / SOURCES.length) * 100}%`, transition: "width .4s" }} />
                </div>
                <div style={{ fontSize: 10, color: "#a1a1aa", marginTop: 4 }}>{indexed} indexed · {SOURCES.length - indexed} pending</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: "auto" }}>
                {SOURCES.map(src => (
                  <div key={src.id}
                    style={{ padding: "8px 10px", borderRadius: 6, border: "1px solid #e4e4e7", background: "#fff", transition: "background .12s", cursor: "default" }}
                    onMouseOver={e => e.currentTarget.style.background = "#fafafa"}
                    onMouseOut={e => e.currentTarget.style.background = "#fff"}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", flexShrink: 0, background: src.indexed ? "#0ea5e9" : "#d1d1d6" }} />
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: 12.5, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{src.title}</div>
                        <div style={{ fontSize: 10, color: "#a1a1aa", marginTop: 1 }}>{src.tag}</div>
                      </div>
                      <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: ".05em", textTransform: "uppercase", padding: "2px 6px", borderRadius: 3, flexShrink: 0, background: src.indexed ? "#f0f9ff" : "#f4f4f5", color: src.indexed ? "#0ea5e9" : "#a1a1aa", border: `1px solid ${src.indexed ? "#bae6fd" : "#e4e4e7"}` }}>
                        {src.indexed ? "Live" : "Pending"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ paddingTop: 12, marginTop: 12, borderTop: "1px solid #e4e4e7" }}>
                <button onClick={handleIngest} disabled={ingestStatus === "running"}
                  style={{ width: "100%", padding: "7px 12px", borderRadius: 6, fontFamily: "inherit", fontSize: 12, fontWeight: 500, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, transition: "all .15s", cursor: ingestStatus === "running" ? "not-allowed" : "pointer", background: ingestStatus === "running" ? "#f4f4f5" : "#111", color: ingestStatus === "running" ? "#a1a1aa" : "#fff", border: `1px solid ${ingestStatus === "running" ? "#e4e4e7" : "#111"}` }}>
                  {ingestStatus === "running" ? <><Spinner size={11} /><span>Syncing…</span></> : "Sync Docs"}
                </button>
                {ingestStatus === "done" && <div style={{ fontSize: 11, color: "#22c55e", textAlign: "center", marginTop: 6, fontWeight: 500 }}>✓ Sync complete</div>}
              </div>
            </div>
          </div>

          {/* CENTER */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0, background: "#fff" }}>
            <div ref={msgsRef} style={{ flex: 1, overflow: "auto", padding: "28px 32px" }}>
              <div style={{ maxWidth: 680, margin: "0 auto" }}>
                {messages.map(m => <Message key={m.id} msg={m} />)}
              </div>
            </div>
            <div style={{ borderTop: "1px solid #e4e4e7", padding: "12px 24px 16px", background: "#fff" }}>
              <div style={{ maxWidth: 680, margin: "0 auto" }}>
                <div style={{ display: "flex", alignItems: "flex-end", gap: 8, border: `1.5px solid ${focused ? "#0ea5e9" : "#e4e4e7"}`, borderRadius: 10, padding: "9px 10px 9px 14px", background: "#fff", transition: "border-color .15s" }}>
                  <textarea ref={inputRef} rows={1} value={input} placeholder="Ask about GitLab's handbook, values, processes…" disabled={busy}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                    onInput={e => { e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 110) + "px"; }}
                    onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
                    style={{ flex: 1, border: "none", outline: "none", resize: "none", fontSize: 13.5, color: "#111", fontFamily: "inherit", lineHeight: 1.6, maxHeight: 110, overflow: "auto", background: "transparent" }}
                  />
                  <button onClick={() => send()} disabled={!canSend}
                    style={{ width: 32, height: 32, borderRadius: 7, border: "none", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", cursor: canSend ? "pointer" : "not-allowed", transition: "all .15s", background: canSend ? "#111" : "#e4e4e7", color: canSend ? "#fff" : "#d1d1d6" }}>
                    {busy ? <Spinner size={13} /> : <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 10.5V2.5M6.5 2.5L3.5 5.5M6.5 2.5L9.5 5.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                  </button>
                </div>
                <div style={{ fontSize: 11, color: "#d1d1d6", marginTop: 5, textAlign: "center" }}>↵ send · ⇧↵ newline · answers grounded in GitLab docs</div>
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div style={{ width: rightOpen ? 236 : 0, minWidth: rightOpen ? 236 : 0, overflow: "hidden", transition: "all .2s ease", borderLeft: "1px solid #e4e4e7", background: "#fafafa", flexShrink: 0 }}>
            <div style={{ padding: 14, height: "100%", overflow: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#a1a1aa", marginBottom: 8 }}>CI/CD Builder</div>
                <CICDGenerator onGenerate={send} disabled={busy} />
              </div>
              <div style={{ height: 1, background: "#e4e4e7" }} />
              <div>
                <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#a1a1aa", marginBottom: 8 }}>Quick Actions</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  {ACTIONS.map(a => (
                    <button key={a.label} disabled={busy} onClick={() => send(a.prompt)}
                      style={{ width: "100%", textAlign: "left", background: "#fff", border: "1px solid #e4e4e7", borderRadius: 6, padding: "8px 11px", cursor: busy ? "not-allowed" : "pointer", fontSize: 12.5, fontWeight: 500, color: "#52525b", fontFamily: "inherit", transition: "all .15s", opacity: busy ? 0.4 : 1 }}
                      onMouseOver={e => { if (!busy) { e.currentTarget.style.borderColor = "#f59e0b"; e.currentTarget.style.color = "#111"; } }}
                      onMouseOut={e => { e.currentTarget.style.borderColor = "#e4e4e7"; e.currentTarget.style.color = "#52525b"; }}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ height: 1, background: "#e4e4e7" }} />
              <div>
                <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "#a1a1aa", marginBottom: 8 }}>Session</div>
                <div style={{ background: "#fff", border: "1px solid #e4e4e7", borderRadius: 6, overflow: "hidden" }}>
                  {[["Queries", messages.filter(m => m.role === "user").length], ["Sources cited", messages.reduce((a, m) => a + (m.sources?.length || 0), 0)], ["Session ID", SESSION_ID.slice(2, 9)]].map(([l, v], i, arr) => (
                    <div key={l} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 11px", borderBottom: i < arr.length - 1 ? "1px solid #e4e4e7" : "none" }}>
                      <span style={{ fontSize: 12, color: "#71717a" }}>{l}</span>
                      <span style={{ fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
              <button onClick={() => setMessages([{ id: "c", role: "bot", text: "Cleared. Ask me anything about GitLab.", sources: [], isNew: true }])}
                style={{ width: "100%", padding: 7, background: "#fff", border: "1px solid #e4e4e7", borderRadius: 6, cursor: "pointer", fontSize: 12, color: "#71717a", fontFamily: "inherit", marginTop: "auto", transition: "all .15s" }}
                onMouseOver={e => { e.currentTarget.style.borderColor = "#d1d1d6"; e.currentTarget.style.color = "#111"; }}
                onMouseOut={e => { e.currentTarget.style.borderColor = "#e4e4e7"; e.currentTarget.style.color = "#71717a"; }}
              >
                Clear chat
              </button>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
