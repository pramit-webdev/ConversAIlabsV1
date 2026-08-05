/* PDF RAG Assistant — chat-style frontend with streaming answers + session history. */
"use strict";

const $ = (id) => document.getElementById(id);

const REFUSAL_TEXT = "The information is not available in the provided documents.";
const STORAGE_KEY = "pdfRagChatV1";

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

/* ------------------------------------------------------------------ */
/* Session history (localStorage)                                      */
/* ------------------------------------------------------------------ */
function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chatState));
  } catch {
    /* storage full / unavailable — chat still works, just not persisted */
  }
}

let chatState = loadState();
let msgSeq = 0;

function renderState() {
  if (!chatState.length) return;
  $("welcome").style.display = "none";
  for (const item of chatState) {
    msgSeq += 1;
    if (item.role === "user") {
      const { body } = addMessage("user");
      body.textContent = item.text;
    } else if (item.role === "assistant") {
      const { body } = addMessage("assistant");
      if (item.available) {
        linkCitations(body, item.text, msgSeq);
        renderSources(body, item.sources || [], msgSeq);
      } else {
        body.classList.add("refusal");
        body.textContent = REFUSAL_TEXT;
      }
    }
  }
  scrollToBottom(true);
}

function newChat() {
  chatState = [];
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
  $("messages").innerHTML = "";
  $("welcome").style.display = "";
  $("question-input").value = "";
  $("question-input").focus();
  setBusy(false);
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
      $("question-input").focus();
    });
    wrap.appendChild(b);
  });
}

function addMessage(role) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;
  const body = document.createElement("div");
  body.className = "bubble";
  msg.appendChild(body);
  $("messages").appendChild(msg);
  return { msg, body };
}

function addUserMessage(text) {
  const { body } = addMessage("user");
  body.textContent = text;
  scrollToBottom(true);
}

function addTyping() {
  const { body } = addMessage("assistant");
  body.classList.add("typing");
  body.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  return body;
}

function renderSources(body, sources, msgId) {
  if (!sources.length) return;
  const wrap = document.createElement("div");
  wrap.className = "sources";
  wrap.innerHTML = `<div class="sources-title">SOURCES</div>`;
  sources.forEach((s, i) => {
    const card = document.createElement("div");
    card.className = "source";
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

function linkCitations(body, text, msgId) {
  body.innerHTML = escapeHtml(text).replace(
    /[\[【](\d+)[\]】]/g,
    (match, n) => {
      const el = document.getElementById(`src-${msgId}-${n}`);
      return el
        ? `<a class="cite" href="#src-${msgId}-${n}" title="Source ${n}">[${n}]</a>`
        : match;
    }
  );
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

  input.value = "";
  autoGrow(input);
  msgSeq += 1;
  chatState.push({ role: "user", text: question });
  saveState();
  addUserMessage(question);
  $("welcome").style.display = "none";
  setBusy(true);

  const typing = addTyping();
  let answerText = "";
  let sources = [];
  let done = false;
  let available = true;

  const finish = (text, isAvailable, srcs) => {
    chatState.push({ role: "assistant", text, available: isAvailable, sources: srcs });
    saveState();
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
          answerText += event.text;
          typing.classList.remove("typing");
          typing.textContent = answerText;
          scrollToBottom();
        } else if (event.type === "available") {
          available = event.available;
        } else if (event.type === "sources") {
          sources = event.sources || [];
        } else if (event.type === "error") {
          typing.classList.remove("typing");
          typing.innerHTML = `<span class="error">Error: ${escapeHtml(event.message)}</span>`;
          done = true;
        } else if (event.type === "done") {
          done = true;
        }
      }
    }
  } catch (err) {
    if (!done) {
      typing.classList.remove("typing");
      typing.innerHTML = `<span class="error">Error: ${escapeHtml(err.message)}</span>`;
      done = true;
    }
  }

  if (done && answerText) {
    const isRefusal = answerText.toLowerCase().includes("not available in the provided documents");
    typing.classList.remove("typing");
    if (isRefusal) {
      available = false;
      sources = [];
      typing.classList.add("refusal");
      typing.textContent = REFUSAL_TEXT;
      finish(REFUSAL_TEXT, false, []);
    } else if (available) {
      typing.textContent = "";
      linkCitations(typing, answerText, msgSeq);
      renderSources(typing, sources, msgSeq);
      finish(answerText, true, sources);
    } else {
      typing.classList.add("refusal");
      typing.textContent = REFUSAL_TEXT;
      finish(REFUSAL_TEXT, false, []);
    }
  } else if (done && !answerText) {
    typing.classList.add("refusal");
    typing.textContent = REFUSAL_TEXT;
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
$("new-chat-btn").addEventListener("click", newChat);
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

renderSuggestions();
renderState();
refreshStatus();
setBusy(false);
