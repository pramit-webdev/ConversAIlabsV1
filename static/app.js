/* Frontend logic for the PDF RAG assistant. */
"use strict";

const $ = (id) => document.getElementById(id);

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return body;
}

async function refreshStatus() {
  try {
    const data = await api("/api/documents");
    const count = data.documents.length;
    const badge = $("doc-count");
    badge.textContent =
      count === 0
        ? "No documents indexed yet"
        : `${count} document${count > 1 ? "s" : ""} · ${data.total_chunks} chunks`;
    badge.className = "badge" + (count > 0 ? " ok" : "");
    if (data.error) {
      $("qdrant-status").textContent = "Qdrant not configured";
      $("qdrant-status").className = "badge warn";
    } else {
      $("qdrant-status").textContent = "Qdrant connected";
      $("qdrant-status").className = "badge ok";
    }
  } catch (err) {
    $("qdrant-status").textContent = "Qdrant not configured";
    $("qdrant-status").className = "badge warn";
  }
  try {
    const m = await api("/api/openrouter/models");
    $("models-info").textContent = `embed: ${m.embedding_model} · generate: ${m.llm_model}`;
  } catch {
    /* non-critical */
  }
}

async function ingestPdfs() {
  const input = $("pdf-input");
  const files = Array.from(input.files || []);
  if (files.length === 0) {
    $("ingest-msg").textContent = "Select at least one PDF first.";
    return;
  }
  const btn = $("ingest-btn");
  btn.disabled = true;
  const msg = $("ingest-msg");
  msg.textContent = `Indexing ${files.length} PDF(s)… this can take a minute per file.`;
  let done = 0;
  for (const file of files) {
    msg.textContent = `Indexing ${file.name} (${++done}/${files.length})…`;
    const form = new FormData();
    form.append("upload", file);
    try {
      const result = await api("/api/ingest", { method: "POST", body: form });
      msg.textContent += ` → ${result.chunks_indexed} chunks`;
    } catch (err) {
      msg.textContent += ` → FAILED: ${err.message}`;
    }
  }
  msg.textContent += "  Done.";
  btn.disabled = false;
  input.value = "";
  refreshStatus();
}

function renderSources(sources) {
  const wrap = $("sources");
  if (!sources.length) {
    wrap.innerHTML = "";
    return;
  }
  const heading = `<div class="muted small" style="margin:10px 0 4px;font-weight:600;">SOURCES</div>`;
  const cards = sources
    .map(
      (s, i) => `
      <div class="source" id="src-${i + 1}">
        <div class="source-head">
          <span class="source-num">${i + 1}</span>
          <span class="source-doc">${escapeHtml(s.document)}</span>
          <span class="source-meta">Page ${s.page} · score ${s.score.toFixed(3)}</span>
        </div>
        <blockquote>${escapeHtml(s.text)}</blockquote>
      </div>`
    )
    .join("");
  wrap.innerHTML = heading + cards;
}

function linkCitations(text) {
  return text.replace(/[\[【](\d+)[\]】]/g, (match, n) => {
    const el = document.getElementById(`src-${n}`);
    if (el) {
      return `<a class="cite" href="#src-${n}" title="Jump to source ${n}">[${n}]</a>`;
    }
    return match;
  });
}

async function askQuestion() {
  const input = $("question-input");
  const question = input.value.trim();
  if (!question) return;

  const btn = $("ask-btn");
  btn.disabled = true;
  $("loading").classList.remove("hidden");
  $("answer-panel").classList.remove("hidden");
  $("answer-text").textContent = "";
  renderSources([]);

  try {
    const data = await api("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const answerEl = $("answer-text");
    if (!data.available) {
      answerEl.className = "not-found";
      answerEl.textContent = data.answer;
    } else {
      answerEl.className = "";
      answerEl.innerHTML = linkCitations(escapeHtml(data.answer));
    }
    renderSources(data.sources);
  } catch (err) {
    $("answer-text").className = "error";
    $("answer-text").textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    $("loading").classList.add("hidden");
  }
}

$("ask-btn").addEventListener("click", askQuestion);
$("question-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") askQuestion();
});
$("ingest-btn").addEventListener("click", ingestPdfs);

refreshStatus();
