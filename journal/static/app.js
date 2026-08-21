const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;

let mediaRecorder = null;
let audioChunks = [];
let recognition = null;
let finalTranscript = "";
let recordedBlob = null;
let isRecording = false;

function showError(msg) {
  const el = document.getElementById("capture-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  const el = document.getElementById("capture-error");
  el.classList.add("hidden");
  el.textContent = "";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---- Tabs ----

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const mode = tab.dataset.mode;
    document.querySelectorAll(".capture-panel").forEach((p) => {
      p.classList.toggle("hidden", p.dataset.panel !== mode);
    });
    hideError();
  });
});

// ---- Shared save flow ----

async function submitEntry(formData, buttonId) {
  const button = document.getElementById(buttonId);
  button.disabled = true;
  hideError();
  try {
    const res = await fetch("/api/entries", { method: "POST", body: formData });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `Save failed (${res.status})`);
    }
    await loadEntries(document.getElementById("search-input").value.trim());
  } catch (err) {
    showError(err.message || "Could not save entry.");
  } finally {
    button.disabled = false;
  }
}

// ---- Write tab ----

document.getElementById("save-typed").addEventListener("click", async () => {
  const textEl = document.getElementById("typed-text");
  const text = textEl.value.trim();
  if (!text) {
    showError("Write something before saving.");
    return;
  }
  const form = new FormData();
  form.append("source", "typed");
  form.append("text", text);
  await submitEntry(form, "save-typed");
  textEl.value = "";
});

// ---- Speak tab ----

function resetVoicePanel() {
  document.getElementById("voice-transcript").value = "";
  document.getElementById("voice-preview").classList.add("hidden");
  document.getElementById("save-voice").classList.add("hidden");
  document.getElementById("record-status").textContent = "";
  recordedBlob = null;
  finalTranscript = "";
}

async function startRecording() {
  resetVoicePanel();

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showError("Microphone access was denied or unavailable. Check your browser's permissions.");
    return;
  }

  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) audioChunks.push(e.data);
  };
  mediaRecorder.onstop = () => {
    recordedBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    const preview = document.getElementById("voice-preview");
    preview.src = URL.createObjectURL(recordedBlob);
    preview.classList.remove("hidden");
    document.getElementById("save-voice").classList.remove("hidden");
    stream.getTracks().forEach((t) => t.stop());
  };
  mediaRecorder.start();

  if (SpeechRecognitionCtor) {
    recognition = new SpeechRecognitionCtor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = navigator.language || "en-US";
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += piece + " ";
        } else {
          interim += piece;
        }
      }
      document.getElementById("voice-transcript").value = (finalTranscript + interim).trim();
    };
    recognition.onerror = (event) => {
      if (event.error !== "no-speech") {
        showError(`Live transcription stopped (${event.error}). Recording continues — you can type the transcript manually.`);
      }
    };
    try {
      recognition.start();
    } catch (e) {
      // already started; ignore
    }
  } else {
    document.getElementById("voice-transcript").placeholder =
      "Live transcription isn't supported in this browser — type what you said here.";
  }

  isRecording = true;
  const toggle = document.getElementById("record-toggle");
  toggle.textContent = "■ Stop recording";
  toggle.classList.add("recording");
  document.getElementById("record-status").textContent = "Recording…";
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  if (recognition) {
    try {
      recognition.stop();
    } catch (e) {
      // ignore
    }
  }
  isRecording = false;
  const toggle = document.getElementById("record-toggle");
  toggle.textContent = "● Start recording";
  toggle.classList.remove("recording");
  document.getElementById("record-status").textContent = "Stopped — review and save below.";
}

document.getElementById("record-toggle").addEventListener("click", () => {
  if (isRecording) stopRecording();
  else startRecording();
});

document.getElementById("save-voice").addEventListener("click", async () => {
  const text = document.getElementById("voice-transcript").value.trim();
  const form = new FormData();
  form.append("source", "voice");
  form.append("text", text);
  if (recordedBlob) form.append("audio", recordedBlob, "recording.webm");
  await submitEntry(form, "save-voice");
  resetVoicePanel();
});

// ---- Upload tab ----

document.getElementById("save-upload").addEventListener("click", async () => {
  const fileInput = document.getElementById("upload-file");
  const transcript = document.getElementById("upload-transcript").value.trim();
  if (!fileInput.files.length) {
    showError("Choose an audio file to upload.");
    return;
  }
  const form = new FormData();
  form.append("source", "upload");
  form.append("text", transcript);
  form.append("audio", fileInput.files[0]);
  await submitEntry(form, "save-upload");
  fileInput.value = "";
  document.getElementById("upload-transcript").value = "";
});

// ---- Entries list ----

let searchDebounce = null;
document.getElementById("search-input").addEventListener("input", (e) => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => loadEntries(e.target.value.trim()), 250);
});

async function loadEntries(q = "") {
  const url = q ? `/api/entries?q=${encodeURIComponent(q)}` : "/api/entries";
  const res = await fetch(url);
  const entries = await res.json();
  renderEntries(entries, q);
}

function renderEntries(entries, q) {
  const container = document.getElementById("entries");
  const emptyState = document.getElementById("empty-state");
  container.querySelectorAll(".entry-card").forEach((el) => el.remove());

  if (!entries.length) {
    emptyState.classList.remove("hidden");
    emptyState.textContent = q
      ? `No entries match "${q}".`
      : "No entries yet — write or speak your first one above.";
    return;
  }
  emptyState.classList.add("hidden");
  for (const entry of entries) {
    container.appendChild(renderEntryCard(entry));
  }
}

function renderEntryCard(entry) {
  const card = document.createElement("article");
  card.className = "entry-card";

  const date = new Date(entry.created_at);
  const dateStr = date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

  const header = document.createElement("div");
  header.className = "entry-header";
  header.innerHTML = `<h3>${escapeHtml(entry.title)}</h3><time>${dateStr}</time>`;
  card.appendChild(header);

  const badges = [];
  if (entry.mood) badges.push(`<span class="badge mood">${escapeHtml(entry.mood)}</span>`);
  for (const tag of entry.tags || []) {
    badges.push(`<span class="badge tag">#${escapeHtml(tag)}</span>`);
  }
  if (badges.length) {
    const meta = document.createElement("div");
    meta.className = "entry-meta";
    meta.innerHTML = badges.join("");
    card.appendChild(meta);
  }

  if (entry.summary) {
    const summary = document.createElement("p");
    summary.className = "entry-summary";
    summary.textContent = entry.summary;
    card.appendChild(summary);
  }

  const body = document.createElement("p");
  body.className = "entry-body";
  body.textContent = entry.body;
  card.appendChild(body);

  if (entry.audio_path) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = `/audio/${entry.audio_path}`;
    card.appendChild(audio);
  }

  return card;
}

loadEntries();
