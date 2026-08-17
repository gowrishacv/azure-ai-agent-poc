import { PublicClientApplication } from "@azure/msal-browser";
import "./styles.css";

const conversation = document.querySelector("#conversation");
const form = document.querySelector("#ask-form");
const question = document.querySelector("#question");
const askButton = document.querySelector("#ask");
const requestState = document.querySelector("#request-state");
const authState = document.querySelector("#auth-state");
const signInButton = document.querySelector("#sign-in");
const signOutButton = document.querySelector("#sign-out");
const newChatButton = document.querySelector("#new-chat");
const characterCount = document.querySelector("#character-count");

let publicConfig;
let authClient;
let account;
let requestInProgress = false;

const welcomeMarkup = `
  <div class="welcome" id="welcome">
    <div class="welcome-icon" aria-hidden="true">AI</div>
    <div>
      <p class="welcome-kicker">AUTHORIZED KNOWLEDGE ASSISTANT</p>
      <h2>What can I help you find?</h2>
      <p>Ask a question about the Azure AI platform. Every answer is grounded in documents you are authorized to retrieve.</p>
    </div>
    <div class="suggestions" aria-label="Suggested questions">
      <button type="button" class="suggestion" data-question="How should production workloads authenticate to Azure services?">
        <span>Identity</span>
        How should production workloads authenticate?
      </button>
      <button type="button" class="suggestion" data-question="What is the private connectivity policy for this platform?">
        <span>Networking</span>
        What is the private connectivity policy?
      </button>
      <button type="button" class="suggestion" data-question="What operational telemetry is collected and what data must not be logged?">
        <span>Operations</span>
        What telemetry is collected?
      </button>
    </div>
  </div>`;

function escapeText(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function renderWelcome() {
  conversation.innerHTML = welcomeMarkup;
  requestState.textContent = "";
  question.value = "";
  updateComposer();
  question.focus();
}

function addMessage(kind, content, citations = [], correlationId = null, options = {}) {
  document.querySelector("#welcome")?.remove();
  const article = document.createElement("article");
  article.className = `message ${kind}${options.error ? " error" : ""}`;
  const citationsMarkup = citations.length
    ? `<section class="sources" aria-label="Sources">
        <div class="sources-heading"><span>Sources</span><span>${citations.length} authorized</span></div>
        <ol>${citations
          .map(
            (citation) =>
              `<li><span class="source-id">${escapeText(citation.id)}</span><span><strong>${escapeText(citation.title)}</strong>` +
              `${citation.source ? `<small>${escapeText(citation.source)}</small>` : ""}</span></li>`,
          )
          .join("")}</ol>
      </section>`
    : "";
  const assistantActions =
    kind === "assistant" && !options.error
      ? `<div class="message-actions">
          <button type="button" class="text-action" data-copy aria-label="Copy answer">Copy</button>
          ${
            correlationId
              ? `<span class="correlation" title="Use this ID when reporting an issue">Request ${escapeText(correlationId.slice(0, 8))}</span>`
              : ""
          }
        </div>`
      : "";
  const feedbackMarkup =
    kind === "assistant" && correlationId && !options.error
      ? `<div class="feedback" data-correlation-id="${escapeText(correlationId)}">
          <span>Was this answer useful?</span>
          <button type="button" data-rating="up" aria-label="Mark answer as useful">Yes</button>
          <button type="button" data-rating="down" aria-label="Mark answer as not useful">No</button>
        </div>`
      : "";
  article.innerHTML = `
    <div class="avatar" aria-hidden="true">${kind === "user" ? "You" : "AI"}</div>
    <div class="message-column">
      <div class="message-body"><p>${escapeText(content)}</p>${citationsMarkup}</div>
      ${assistantActions}${feedbackMarkup}
    </div>
  `;
  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

function addLoadingMessage() {
  document.querySelector("#welcome")?.remove();
  const article = document.createElement("article");
  article.className = "message assistant loading-message";
  article.setAttribute("role", "status");
  article.innerHTML = `
    <div class="avatar" aria-hidden="true">AI</div>
    <div class="message-body loading-body">
      <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>
      <span class="loading-label">Searching authorized sources</span>
    </div>`;
  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

function updateComposer() {
  characterCount.textContent = `${question.value.length} / 2000`;
  question.style.height = "auto";
  question.style.height = `${Math.min(question.scrollHeight, 180)}px`;
}

async function initializeAuthentication() {
  const response = await fetch("/config", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Unable to load application configuration");
  publicConfig = await response.json();
  if (!publicConfig.auth_enabled) {
    authState.textContent = publicConfig.document_authorization_enabled
      ? "Anonymous · public documents"
      : "POC anonymous mode";
    askButton.disabled = false;
    return;
  }
  if (!publicConfig.tenant_id || !publicConfig.client_id || !publicConfig.api_scope) {
    authState.textContent = "Entra authentication configuration is incomplete";
    askButton.disabled = true;
    return;
  }
  authClient = new PublicClientApplication({
    auth: {
      clientId: publicConfig.client_id,
      authority: `https://login.microsoftonline.com/${publicConfig.tenant_id}`,
      redirectUri: window.location.origin,
      postLogoutRedirectUri: window.location.origin,
    },
    cache: { cacheLocation: "sessionStorage" },
  });
  await authClient.initialize();
  const redirectResult = await authClient.handleRedirectPromise();
  account = redirectResult?.account ?? authClient.getAllAccounts()[0];
  renderAuthentication();
}

function renderAuthentication() {
  const authenticated = Boolean(account);
  authState.textContent = authenticated ? account.username : "Sign in required";
  authState.classList.toggle("authenticated", authenticated);
  signInButton.hidden = authenticated;
  signOutButton.hidden = !authenticated;
  askButton.disabled = !authenticated;
}

async function accessToken() {
  if (!publicConfig.auth_enabled) return null;
  if (!account) throw new Error("Sign in before asking a question");
  const request = { account, scopes: [publicConfig.api_scope] };
  try {
    return (await authClient.acquireTokenSilent(request)).accessToken;
  } catch {
    await authClient.acquireTokenRedirect(request);
    return null;
  }
}

async function sendFeedback(correlationId, rating, container) {
  const token = await accessToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch("/feedback", {
    method: "POST",
    headers,
    body: JSON.stringify({ correlation_id: correlationId, rating }),
  });
  if (!response.ok) throw new Error("Feedback was not accepted");
  container.textContent = "Thank you for the feedback.";
}

conversation.addEventListener("click", async (event) => {
  const suggestion = event.target.closest("button[data-question]");
  if (suggestion) {
    question.value = suggestion.dataset.question;
    updateComposer();
    question.focus();
    return;
  }

  const copyButton = event.target.closest("button[data-copy]");
  if (copyButton) {
    const text = copyButton.closest(".message-column").querySelector(".message-body > p").textContent;
    await navigator.clipboard.writeText(text);
    copyButton.textContent = "Copied";
    window.setTimeout(() => (copyButton.textContent = "Copy"), 1600);
    return;
  }

  const ratingButton = event.target.closest("button[data-rating]");
  if (!ratingButton) return;
  const container = ratingButton.closest(".feedback");
  try {
    await sendFeedback(container.dataset.correlationId, ratingButton.dataset.rating, container);
  } catch (error) {
    container.querySelector("span").textContent = error.message;
  }
});

signInButton.addEventListener("click", () =>
  authClient.loginRedirect({ scopes: [publicConfig.api_scope] }),
);
signOutButton.addEventListener("click", () => authClient.logoutRedirect({ account }));
newChatButton.addEventListener("click", renderWelcome);

question.addEventListener("input", updateComposer);
question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (text.length < 3 || requestInProgress) return;
  requestInProgress = true;
  newChatButton.disabled = true;
  addMessage("user", text);
  question.value = "";
  updateComposer();
  askButton.disabled = true;
  requestState.textContent = "Retrieving authorized sources…";
  const loadingMessage = addLoadingMessage();
  try {
    const token = await accessToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch("/ask", {
      method: "POST",
      headers,
      body: JSON.stringify({ question: text }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "The assistant is unavailable");
    loadingMessage.remove();
    addMessage("assistant", body.answer, body.citations, body.correlation_id);
  } catch (error) {
    loadingMessage.remove();
    addMessage("assistant", error.message, [], null, { error: true });
  } finally {
    requestInProgress = false;
    newChatButton.disabled = false;
    askButton.disabled = publicConfig.auth_enabled && !account;
    requestState.textContent = "";
    question.focus();
  }
});

updateComposer();
initializeAuthentication().catch((error) => {
  authState.textContent = error.message;
  askButton.disabled = true;
});
