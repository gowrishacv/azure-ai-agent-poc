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

let publicConfig;
let authClient;
let account;

function escapeText(value) {
  const node = document.createElement("span");
  node.textContent = value;
  return node.innerHTML;
}

function addMessage(kind, content, citations = [], correlationId = null) {
  const article = document.createElement("article");
  article.className = `message ${kind}`;
  const citationsMarkup = citations.length
    ? `<ul class="citations">${citations
        .map(
          (citation) =>
            `<li><strong>${escapeText(citation.id)}</strong> ${escapeText(citation.title)}` +
            `${citation.source ? ` · ${escapeText(citation.source)}` : ""}</li>`,
        )
        .join("")}</ul>`
    : "";
  const feedbackMarkup =
    kind === "assistant" && correlationId
      ? `<div class="feedback" data-correlation-id="${escapeText(correlationId)}">
          <span>Was this useful?</span>
          <button type="button" data-rating="up" aria-label="Useful answer">Yes</button>
          <button type="button" data-rating="down" aria-label="Not useful">No</button>
        </div>`
      : "";
  article.innerHTML = `
    <div class="avatar" aria-hidden="true">${kind === "user" ? "You" : "AI"}</div>
    <div class="message-body"><p>${escapeText(content)}</p>${citationsMarkup}${feedbackMarkup}</div>
  `;
  conversation.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function initializeAuthentication() {
  const response = await fetch("/config", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Unable to load application configuration");
  publicConfig = await response.json();
  if (!publicConfig.auth_enabled) {
    authState.textContent = publicConfig.document_authorization_enabled
      ? "Anonymous · public documents"
      : "POC anonymous mode";
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
  authState.textContent = authenticated ? `Signed in as ${account.username}` : "Sign in required";
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
  const button = event.target.closest("button[data-rating]");
  if (!button) return;
  const container = button.closest(".feedback");
  try {
    await sendFeedback(container.dataset.correlationId, button.dataset.rating, container);
  } catch (error) {
    container.querySelector("span").textContent = error.message;
  }
});

signInButton.addEventListener("click", () =>
  authClient.loginRedirect({ scopes: [publicConfig.api_scope] }),
);
signOutButton.addEventListener("click", () => authClient.logoutRedirect({ account }));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (text.length < 3) return;
  addMessage("user", text);
  question.value = "";
  askButton.disabled = true;
  requestState.textContent = "Retrieving authorized sources…";
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
    addMessage("assistant", body.answer, body.citations, body.correlation_id);
  } catch (error) {
    addMessage("assistant", error.message);
  } finally {
    askButton.disabled = publicConfig.auth_enabled && !account;
    requestState.textContent = "";
    question.focus();
  }
});

initializeAuthentication().catch((error) => {
  authState.textContent = error.message;
  askButton.disabled = true;
});
