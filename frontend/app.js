// Leave empty when frontend and backend are on the same site (Vercel, or localhost:8000).
// For a separately hosted backend, put its URL here, e.g. "https://my-backend.vercel.app"
const API_URL = "http://127.0.0.1:8000";

const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const starters = document.getElementById("starters");
const themeBtn = document.getElementById("theme");

/* ---------- Light / dark theme ---------- */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeBtn.setAttribute(
    "aria-label",
    theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
  );
}

applyTheme(document.documentElement.dataset.theme || "light");

themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem("theme", next);
  } catch (e) {}
});

/* ---------- Messages ---------- */
function addMsg(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function addTyping() {
  const div = document.createElement("div");
  div.className = "msg bot typing";
  div.setAttribute("aria-label", "Assistant is typing");
  div.innerHTML = "<span></span><span></span><span></span>";
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function draw(div, full) {
  const reply = full.split("|||")[0].trim();
  const isTransfer = reply.startsWith("[TRANSFER]");
  div.className = "msg bot" + (isTransfer ? " transfer" : "");
  div.textContent = reply.replace(/^\[(REPLY|TRANSFER)\]\s*/, "");
  chat.scrollTop = chat.scrollHeight;
}

// draw at most once per frame so fast streaming stays smooth
let frame = 0;
let latest = "";
function paint(div, full) {
  latest = full;
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    draw(div, latest);
  });
}

/* ---------- Sending ---------- */
starters.addEventListener("click", (e) => {
  const btn = e.target.closest(".starter");
  if (!btn) return;
  input.value = btn.textContent;
  form.requestSubmit();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message || sendBtn.disabled) return;

  starters.remove();
  addMsg(message, "user");
  input.value = "";
  sendBtn.disabled = true;

  const botDiv = addTyping();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  let full = "";

  try {
    const res = await fetch(API_URL + "/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal: controller.signal
    });
    if (!res.ok) throw new Error("bad status " + res.status);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      full += decoder.decode(value, { stream: true });
      paint(botDiv, full);
    }

    cancelAnimationFrame(frame);
    frame = 0;
    draw(botDiv, full);
  } catch (err) {
    botDiv.className = "msg bot";
    botDiv.textContent =
      err.name === "AbortError"
        ? "This is taking longer than usual. Send your message again in a moment."
        : "Couldn't reach the assistant. Check your connection and send your message again.";
  } finally {
    clearTimeout(timer);
    sendBtn.disabled = false;
    input.focus();
  }
});