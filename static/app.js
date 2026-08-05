/* PDF RAG Assistant — DeepSeek-style chat with sidebar threads + streaming. */
"use strict";

const $ = (id) => document.getElementById(id);

const REFUSAL_TEXT = "The information is not available in the provided documents.";
const STORAGE_KEY = "pdfRagThreadsV1";
const LEGACY_KEY = "pdfRagChatV1";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}

function scrollToBottom(force = false) {
  const scroller = $("chat");
  if (!scroller) return;
  const nearBottom =
    scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 160;
  if (force || nearBottom) scroller.scrollTop = scroller.scrollHeight;
}

function newThreadId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

/* ------------------------------------------------------------------ */
/* Thread store (localStorage)                                         */
/* ------------------------------------------------------------------ */
function loadStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.threads)) return parsed;
    }
    const legacy = localStorage.getItem(LEGACY_KEY);
    if (legacy) {
      const msgs = JSON.parse(legacy);
      if (Array.isArray(msgs)) {
        const t = { id: newThreadId(), title: "Imported chat", messages: msgs };
        return { threads: [t], activeId: t.id };
      }
    }
  } catch {
    /* fall through to fresh store */
  }
  return { threads: [], activeId: null };
}

let store = loadStore();

function saveStore() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    /* storage unavailable — chat still works, just not persisted */
  }
}

function activeThread() {
  return store.threads.find((t) => t.id === store.activeId) || null;
}

function ensureActiveThread() {
  if (activeThread()) return activeThread();
  const t = { id: newThreadId(), title: "New chat", messages: [] };
  store.threads.push(t);
  store.activeId = t.id;
  saveStore();
  return t;
}

/* ------------------------------------------------------------------ */
/* Sidebar                                                             */
/* ------------------------------------------------------------------ */
function renderSidebar() {
  const list = $("thread-list");
  list.innerHTML = "";
  store.threads.forEach((t) => {
    const item = document.createElement("div");
    item.className = "thread-item" + (t.id === store.activeId ? " active" : "");

    const label = document.createElement("span");
    label.className = "thread-title";
    label.textContent = t.title;
    label.title = t.title;

    const del = document.createElement("button");
    del.className = "thread-del";
    del.textContent = "×";
    del.title = "Delete chat";
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteThread(t.id);
    });

    item.appendChild(label);
    item.appendChild(del);
    item.addEventListener("click", () => openThread(t.id));
    list.appendChild(item);
  });
}

function openThread(id) {
  if (!store.threads.find((t) => t.id === id)) return;
  store.activeId = id;
  saveStore();
  renderSidebar();
  renderThread(activeThread());
}

function newChat() {
  const t = { id: newThreadId(), title: "New chat", messages: [] };
  store.threads.push(t);
  store.activeId = t.id;
  saveStore();
  renderSidebar();
  renderThread(t);
  $("question-input").value = "";
  $("question-input").focus();
  setBusy(false);
}

function deleteThread(id) {
  store.threads = store.threads.filter((t) => t.id !== id);
  if (store.activeId === id) {
    store.activeId = store.threads.length ? store.threads[store.threads.length - 1].id : null;
  }
  saveStore();
  renderSidebar();
  const t = activeThread();
  if (t) renderThread(t);
  else newChat();
  if (!store.threads.length) $("welcome").style.display = "";
}

/* ------------------------------------------------------------------ */
/* Thread rendering                                                    */
/* ------------------------------------------------------------------ */
let msgSeq = 0;

function renderThread(thread) {
  $("messages").innerHTML = "";
  msgSeq = 0;
  if (!thread || !thread.messages.length) {
    $("welcome").style.display = "";
    return;
  }
  $("welcome").style.display = "none";
  for (const item of thread.messages) {
    msgSeq += 1;
    if (item.role === "user") {
      const { content } = addMessage("user");
      content.textContent = item.text;
    } else if (item.role === "assistant") {
      const { content } = addMessage("assistant");
      if (item.available) {
        const md = document.createElement("div");
        md.className = "md";
        md.innerHTML = mdToHtml(item.text, msgSeq);
        content.appendChild(md);
        renderSources(content, item.sources || [], msgSeq);
        wireCopyButtons(md);
      } else {
        content.classList.add("refusal");
        content.textContent = REFUSAL_TEXT;
      }
    }
  }
  scrollToBottom(true);
}

/* ------------------------------------------------------------------ */
/* Message rendering                                                   */
/* ------------------------------------------------------------------ */
const SUGGESTIONS = [
  "Is the right to privacy a fundamental right under the Indian Constitution?",
  "Is it mandatory for the police to register an FIR when a cognizable offence is reported?",
  "What is the permissible limit of reservation under the Constitution?",
  "What is the best recipe for chocolate cake?",
];

function renderSuggestions() {
  const wrap = $("suggestions");
  wrap.innerHTML = "";
  SUGGESTIONS.forEach((q) => {
    const b = document.createElement("button");
    b.className = "suggestion";
    b.textContent = q;
    b.addEventListener("click", () => {
      $("question-input").value = q;
      askQuestion();
    });
    wrap.appendChild(b);
  });
}

function addMessage(role) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;
  const content = document.createElement("div");
  content.className = "content";
  msg.appendChild(content);
  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "▣";
    msg.appendChild(avatar);
  }
  $("messages").appendChild(msg);
  return { msg, content };
}

function addUserMessage(text) {
  const { content } = addMessage("user");
  content.textContent = text;
  scrollToBottom(true);
}

function addTyping() {
  const { content } = addMessage("assistant");
  const bubble = document.createElement("div");
  bubble.className = "typing";
  bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  const textEl = document.createElement("div");
  textEl.className = "stream-text";
  bubble.appendChild(textEl);
  content.appendChild(bubble);
  return { bubble, textEl, content };
}

function renderSources(body, sources, msgId) {
  if (!sources.length) return;
  const old = body.querySelector(".sources");
  if (old) old.remove();
  const wrap = document.createElement("div");
  wrap.className = "sources";
  wrap.innerHTML = `<div class="sources-title">SOURCES</div>`;
  sources.forEach((s, i) => {
    const card = document.createElement("div");
    card.className = "source";
    card.dataset.idx = String(s.idx || i + 1);
    card.id = `src-${msgId}-${i + 1}`;
    card.innerHTML = `
      <div class="source-head">
        <span class="source-num">${i + 1}</span>
        <span class="source-doc">${escapeHtml(s.document)}</span>
        <span class="source-meta">Page ${s.page} · score ${s.score.toFixed(3)}</span>
      </div>
      <blockquote>${escapeHtml(s.text)}</blockquote>`;
    wrap.appendChild(card);
  });
  body.appendChild(wrap);
}

function inlineMd(text, msgId) {
  let s = text;
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/[\[【](\d+)[\]】]/g, (match, n) => {
    const el = document.getElementById(`src-${msgId}-${n}`);
    return el ? `<a class="cite" href="#src-${msgId}-${n}" title="Source ${n}">[${n}]</a>` : match;
  });
  return s;
}

function tableMd(rows) {
  const cells = (row) => row.split("|").slice(1, -1).map((c) => c.trim());
  let t = "<table><thead><tr>" + cells(rows[0]).map((h) => `<th>${inlineMd(h)}</th>`).join("") + "</tr></thead><tbody>";
  for (const row of rows.slice(2)) {
    t += "<tr>" + cells(row).map((c) => `<td>${inlineMd(c)}</td>`).join("") + "</tr>";
  }
  return t + "</tbody></table>";
}

function mdToHtml(src, msgId) {
  const blocks = [];
  let html = escapeHtml(String(src || ""));
  html = html.replace(/```([\w-]*)\n?([\s\S]*?)```/g, (m, lang, body) => {
    blocks.push({ lang, body });
    return `\u0000CODE${blocks.length - 1}\u0000`;
  });
  const lines = html.split("\n");
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^\|/.test(line) && /^\|[\s:\-|]+\|?$/.test(lines[i + 1] || "")) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i]) && lines[i].trim() !== "") rows.push(lines[i++]);
      out.push(tableMd(rows));
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      const lvl = Math.min(heading[1].length, 4);
      out.push(`<h${lvl}>${inlineMd(heading[2], msgId)}</h${lvl}>`);
      i++;
      continue;
    }
    if (/^\s*(---+|\*\*\*+|___+)\s*$/.test(line)) {
      out.push("<hr>");
      i++;
      continue;
    }
    if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
      const ordered = /^\s*\d+[.)]\s+/.test(line);
      const items = [];
      while (i < lines.length && (/^\s*[-*+]\s+/.test(lines[i]) || /^\s*\d+[.)]\s+/.test(lines[i]))) {
        items.push(`<li>${inlineMd(lines[i].replace(/^\s*[-*+]\s+/, "").replace(/^\s*\d+[.)]\s+/, ""), msgId)}</li>`);
        i++;
      }
      out.push(ordered ? `<ol>${items.join("")}</ol>` : `<ul>${items.join("")}</ul>`);
      continue;
    }
    if (/^&gt;/.test(line)) {
      const q = [];
      while (i < lines.length && /^&gt;/.test(lines[i])) q.push(lines[i++].replace(/^&gt;\s?/, ""));
      out.push(`<blockquote>${inlineMd(q.join(" "), msgId)}</blockquote>`);
      continue;
    }
    if (line.indexOf("\u0000CODE") !== -1) {
      out.push(line);
      i++;
      continue;
    }
    if (line.trim() === "") {
      i++;
      continue;
    }
    const para = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      lines[i].indexOf("\u0000CODE") === -1 &&
      !/^&gt;/.test(lines[i]) &&
      !/^\s*[-*+]\s+/.test(lines[i]) &&
      !/^\s*\d+[.)]\s+/.test(lines[i]) &&
      !/^\|/.test(lines[i]) &&
      !/^(#{1,6})\s/.test(lines[i]) &&
      !/^\s*(---+|\*\*\*+|___+)\s*$/.test(lines[i])
    ) {
      para.push(lines[i++]);
    }
    out.push(`<p>${inlineMd(para.join("\n"), msgId)}</p>`);
  }
  html = out.join("\n");
  return html.replace(/\u0000CODE(\d+)\u0000/g, (m, n) => {
    const b = blocks[+n];
    return `<pre><code class="lang-${b.lang || "plain"}">${b.body}</code></pre>`;
  });
}

function wireCopyButtons(root) {
  root.querySelectorAll("pre").forEach((pre) => {
    if (pre.querySelector(".copy-btn")) return;
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      const code = pre.querySelector("code");
      try {
        await navigator.clipboard.writeText(code.innerText);
        btn.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.textContent = "Copy";
          btn.classList.remove("copied");
        }, 1500);
      } catch {
        btn.textContent = "Copy";
      }
    });
    pre.appendChild(btn);
  });
}

/* ------------------------------------------------------------------ */
/* Status / upload                                                     */
/* ------------------------------------------------------------------ */
async function refreshStatus() {
  try {
    const data = await api("/api/documents");
    const n = data.documents.length;
    $("doc-count").textContent =
      n === 0 ? "0 documents" : `${n} documents · ${data.total_chunks} chunks`;
    $("doc-count").className = "badge" + (n > 0 ? " ok" : "");
    $("qdrant-status").textContent = data.error ? "Qdrant not configured" : "Qdrant connected";
    $("qdrant-status").className = "badge" + (data.error ? " warn" : " ok");
  } catch {
    $("qdrant-status").textContent = "Qdrant unreachable";
    $("qdrant-status").className = "badge warn";
  }
}

async function ingestPdfs() {
  const input = $("pdf-input");
  const files = Array.from(input.files || []);
  if (!files.length) return;
  const msg = $("ingest-msg");
  msg.hidden = false;
  msg.className = "ingest-msg notice";
  msg.textContent =
    files.length === 1
      ? `Indexing ${files[0].name}… please wait before asking questions about it.`
      : `Indexing ${files.length} PDFs… please wait before asking questions about them.`;
  let done = 0;
  for (const file of files) {
    msg.textContent = `Indexing ${file.name} (${++done}/${files.length})… please wait before asking questions about it.`;
    const form = new FormData();
    form.append("upload", file);
    try {
      const result = await api("/api/ingest", { method: "POST", body: form });
      msg.textContent += ` → ${result.chunks_indexed} chunks`;
    } catch (err) {
      msg.textContent += ` → FAILED: ${err.message}`;
    }
  }
  msg.className = "ingest-msg notice ok";
  msg.textContent =
    files.length === 1
      ? "Done — new document indexed. Wait a moment before asking questions about it."
      : `Done — ${files.length} documents indexed. Wait a moment before asking questions about them.`;
  input.value = "";
  refreshStatus();
  setTimeout(() => {
    msg.hidden = true;
    msg.className = "ingest-msg";
  }, 12000);
}

/* ------------------------------------------------------------------ */
/* Streaming ask                                                       */
/* ------------------------------------------------------------------ */
async function askQuestion() {
  const input = $("question-input");
  const question = input.value.trim();
  if (!question) return;

  const thread = ensureActiveThread();

  input.value = "";
  autoGrow(input);
  if (!thread.messages.length) {
    thread.title = question.length > 48 ? question.slice(0, 48) + "…" : question;
  }
  msgSeq += 1;
  thread.messages.push({ role: "user", text: question });
  saveStore();
  renderSidebar();
  addUserMessage(question);
  $("welcome").style.display = "none";
  setBusy(true);

  const { bubble, textEl, content } = addTyping();
  let answerText = "";
  let pending = "";
  let rafId = null;
  let started = false;
  let sources = [];
  let sourcesShown = false;
  let done = false;
  let available = true;

  textEl.textContent = "Searching the documents…";

  const flush = () => {
    rafId = null;
    if (!pending) return;
    answerText += pending;
    pending = "";
    if (!started) {
      started = true;
      bubble.classList.remove("typing");
    }
    textEl.innerHTML = mdToHtml(answerText, msgSeq);
    scrollToBottom();
  };

  const finish = (text, isAvailable, srcs) => {
    thread.messages.push({ role: "assistant", text, available: isAvailable, sources: srcs });
    saveStore();
  };

  try {
    const res = await fetch("/api/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    if (!res.body) throw new Error("Streaming not supported by this browser.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done: streamDone } = await reader.read();
      if (streamDone) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const raw = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (!raw.startsWith("data: ")) continue;
        let event;
        try {
          event = JSON.parse(raw.slice(6));
        } catch {
          continue;
        }
        if (event.type === "token") {
          pending += event.text;
          if (!rafId) rafId = requestAnimationFrame(flush);
        } else if (event.type === "available") {
          available = event.available;
          if (available && !started) textEl.textContent = "Generating answer…";
        } else if (event.type === "sources") {
          sources = event.sources || [];
          if (!sourcesShown) {
            sourcesShown = true;
            renderSources(content, sources, msgSeq);
          }
        } else if (event.type === "error") {
          bubble.classList.remove("typing");
          bubble.innerHTML = `<span class="error">Error: ${escapeHtml(event.message)}</span>`;
          done = true;
        } else if (event.type === "done") {
          done = true;
        }
      }
    }
  } catch (err) {
    if (!done) {
      bubble.classList.remove("typing");
      bubble.innerHTML = `<span class="error">Error: ${escapeHtml(err.message)}</span>`;
      done = true;
    }
  }

  if (rafId) cancelAnimationFrame(rafId);
  flush();

  if (done && answerText) {
    const isRefusal = answerText.toLowerCase().includes("not available in the provided documents");
    bubble.classList.remove("typing");
    if (isRefusal) {
      available = false;
      sources = [];
      content.classList.add("refusal");
      content.textContent = REFUSAL_TEXT;
      finish(REFUSAL_TEXT, false, []);
    } else if (available) {
      const md = document.createElement("div");
      md.className = "md";
      md.innerHTML = mdToHtml(answerText, msgSeq);
      bubble.remove();
      content.insertBefore(md, content.querySelector(".sources") || null);
      wireCopyButtons(md);
      const citedIdx = new Set((sources || []).map((s) => s.idx));
      if (citedIdx.size) {
        content.querySelectorAll(".source").forEach((card) => {
          if (!citedIdx.has(Number(card.dataset.idx))) {
            card.classList.add("removing");
            setTimeout(() => card.remove(), 320);
          }
        });
      }
      finish(answerText, true, sources);
    } else {
      content.classList.add("refusal");
      content.textContent = REFUSAL_TEXT;
      finish(REFUSAL_TEXT, false, []);
    }
  } else if (done && !answerText) {
    content.classList.add("refusal");
    content.textContent = REFUSAL_TEXT;
    finish(REFUSAL_TEXT, false, []);
  }

  scrollToBottom(true);
  setBusy(false);
}

/* ------------------------------------------------------------------ */
/* Composer / wiring                                                    */
/* ------------------------------------------------------------------ */
function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
}

function setBusy(busy) {
  $("ask-btn").disabled = busy || !$("question-input").value.trim();
}

$("ask-btn").addEventListener("click", askQuestion);
$("new-chat-sidebar-btn").addEventListener("click", newChat);
$("question-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    askQuestion();
  }
});
$("question-input").addEventListener("input", (e) => {
  autoGrow(e.target);
  setBusy(false);
});
$("pdf-input").addEventListener("change", ingestPdfs);
$("sidebar-toggle").addEventListener("click", () => {
  document.body.classList.toggle("sidebar-open");
});
$("sidebar-toggle-side").addEventListener("click", () => {
  document.body.classList.remove("sidebar-open");
});

renderSuggestions();
renderSidebar();
ensureActiveThread();
renderThread(activeThread());
refreshStatus();
setBusy(false);
