const $ = (id) => document.getElementById(id);
let current = null, recorder = null, chunks = [];

// Anything that came from a person or a file goes through esc() before it
// touches innerHTML. A label is typed text, not markup.
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts = {}) {
  const r = await fetch("/api" + path, opts);
  if (!r.ok) {
    const body = await r.text();
    let msg = body;
    try { msg = JSON.parse(body).detail || body; } catch (e) { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

async function loadHealth() {
  try {
    const h = await api("/health");
    $("health").innerHTML =
      `STT <b>${esc(h.stt.backend)} ${esc(h.stt.model)}</b> · LLM <b class="${h.llm.ok ? "ok" : "bad"}">${h.llm.ok ? esc(h.llm.info) : "not reachable"}</b>` +
      ` · retention ${esc(h.storage.retention_days)}d${h.storage.delete_audio_on_sign ? " · audio deleted on sign" : ""}`;
  } catch (e) { $("health").textContent = "server error: " + e.message; }
}

async function loadTemplates() {
  const t = await api("/templates");
  $("template").innerHTML = t.map(x => `<option ${x === "soap" ? "selected" : ""}>${esc(x)}</option>`).join("");
}

async function loadSessions() {
  const list = await api("/sessions");
  $("list").innerHTML = list.map(m =>
    `<li data-id="${esc(m.id)}" class="${m.id === current ? "active" : ""}">
       <div>${esc(m.label) || "(no label)"}</div>
       <div class="s">${esc(m.id)} · ${esc(m.status)} · ${Math.round(m.audio_seconds)}s</div></li>`).join("");
  for (const li of $("list").querySelectorAll("li")) li.onclick = () => open(li.dataset.id);
}

async function open(id) {
  current = id;
  const s = await api("/sessions/" + id);
  $("transcript").textContent = s.transcript || "Not transcribed yet.";
  $("transcript").classList.toggle("muted", !s.transcript);
  $("note").value = s.note || "";
  const signed = s.meta.status === "signed";
  $("note").disabled = signed;
  const warnings = s.meta.warnings || [];
  $("warnings").hidden = warnings.length === 0;
  $("warnings").textContent = warnings.join("\n");
  $("draftbadge").textContent = signed ? `SIGNED ${s.meta.signed_at}` : "DRAFT · not signed";
  $("draftbadge").classList.toggle("signed", signed);
  $("transcribe").disabled = signed;
  $("draft").disabled = !s.transcript || signed;
  $("save").disabled = signed || !s.note;
  $("copy").disabled = !s.note;
  $("sign").disabled = signed || !s.note;
  loadSessions();
}

async function upload(blob, name) {
  const fd = new FormData();
  fd.append("file", blob, name);
  fd.append("label", $("label").value);
  const meta = await api("/sessions", { method: "POST", body: fd });
  $("label").value = "";
  await open(meta.id);
  await transcribe();
}

async function transcribe() {
  $("transcribe").disabled = true;
  $("transcript").textContent = "Transcribing…";
  try { await api(`/sessions/${current}/transcribe`, { method: "POST" }); }
  catch (e) { alert(e.message); }
  await open(current);
}

async function draft() {
  $("draft").disabled = true;
  $("note").value = "Drafting…";
  try {
    await api(`/sessions/${current}/draft`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template: $("template").value, instructions: $("instructions").value }) });
  } catch (e) { alert(e.message); }
  await open(current);
}

$("transcribe").onclick = transcribe;
$("draft").onclick = draft;
$("save").onclick = async () => {
  try {
    await api(`/sessions/${current}/note`, { method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("note").value }) });
  } catch (e) { alert(e.message); return open(current); }
  $("save").textContent = "Saved"; setTimeout(() => $("save").textContent = "Save edits", 1200);
};
$("copy").onclick = () => navigator.clipboard.writeText($("note").value);
$("sign").onclick = async () => {
  if (!confirm("Sign this note? You are attesting that you reviewed and edited it. The audio will be deleted if that policy is on.")) return;
  try {
    await api(`/sessions/${current}/note`, { method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: $("note").value }) });
    await api(`/sessions/${current}/sign`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signer: "" }) });
  } catch (e) { alert(e.message); }
  await open(current);
};

$("file").onchange = (e) => { if (e.target.files[0]) upload(e.target.files[0], e.target.files[0].name); };

$("rec").onclick = async () => {
  if (recorder && recorder.state === "recording") { recorder.stop(); return; }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  recorder = new MediaRecorder(stream);
  chunks = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.onstop = async () => {
    stream.getTracks().forEach(t => t.stop());
    $("rec").textContent = "● Record"; $("rec").classList.remove("on"); $("recstatus").textContent = "uploading…";
    await upload(new Blob(chunks, { type: recorder.mimeType }), "recording.webm");
    $("recstatus").textContent = "";
  };
  recorder.start();
  $("rec").textContent = "■ Stop"; $("rec").classList.add("on");
  const t0 = Date.now();
  const tick = setInterval(() => {
    if (recorder.state !== "recording") return clearInterval(tick);
    $("recstatus").textContent = "recording " + Math.round((Date.now() - t0) / 1000) + "s";
  }, 500);
};

loadHealth(); loadTemplates(); loadSessions();
