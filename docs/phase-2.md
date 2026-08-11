# Phase 2: authenticated, authorization-aware RAG

Phase 2.1 turns the POC API into a cost-neutral internal chat experience. It
adds no Azure service. The browser UI is compiled into the existing Container
Apps image, and the application continues to scale to zero in development.

## Implemented in Phase 2.1

- responsive citation-first chat UI;
- Microsoft Entra sign-in with the supported `@azure/msal-browser` package;
- JWT signature, issuer, audience, delegated-scope, and optional app-role
  validation;
- deterministic document authorization using Azure AI Search security filters;
- explicit `public`, `user:<id>`, `group:<id>`, and `role:<value>` principals;
- correlation IDs on requests and responses;
- privacy-safe thumbs-up/down feedback telemetry;
- fail-closed indexing when a document has missing or invalid authorization
  metadata;
- Azure DevOps UI build validation.

## Request flow

```text
Browser
  → Entra authorization-code flow with PKCE
  → access token for access_as_user
  → POST /ask
  → validate signature + issuer + audience + scope + optional role
  → derive public/user/group/role principals
  → apply allowed_principals filter to hybrid search
  → send only authorized sources to Foundry
  → return grounded answer, citations, and correlation ID
```

The model never decides authorization. Documents are removed by the Search
filter before their content can enter the model prompt.

## Entra registrations

Create two single-tenant app registrations so browser and API responsibilities
stay separate.

### API application

1. Record the API application's client ID and tenant ID.
2. Under **Expose an API**, keep or create the Application ID URI and add the
   delegated scope `access_as_user`.
3. Optionally create the user app role `AI.Agent.User` and assign approved
   users or groups through the Enterprise Application.
4. Under **Token configuration**, add security-group claims if group-based
   document authorization is required.
5. Set `auth_audience` to the exact `aud` value emitted in an access token. For
   Microsoft identity platform v2 tokens this is normally the API client ID.

### Browser SPA application

1. Add a **Single-page application** platform.
2. Add the Container App origin and local development origin as redirect URIs,
   for example `https://<app-fqdn>` and `http://localhost:8000`.
3. Add delegated permission to the API's `access_as_user` scope.
4. Grant tenant consent according to the organization's policy.
5. Use this registration's client ID as `ui_client_id`.

Do not create a client secret for the SPA. MSAL Browser uses authorization code
flow with PKCE.

## Terraform activation

Copy `infra/environments/prod.example.tfvars` to an environment-specific file
and set:

```hcl
require_auth                  = true
auth_tenant_id                = "<tenant-id>"
auth_audience                 = "<api-client-id>"
auth_required_scope           = "access_as_user"
auth_required_role            = "AI.Agent.User" # optional
auth_scope                    = "api://<api-client-id>/access_as_user"
ui_client_id                  = "<spa-client-id>"
enable_document_authorization = true
```

Use variable-group or generated `.tfvars` values for real identifiers. Do not
commit tenant-specific values to a public repository.

## Document authorization contract

Every source document must declare at least one allowed principal:

```json
{
  "id": "network-001",
  "title": "Private connectivity policy",
  "allowed_principals": [
    "group:00000000-0000-0000-0000-000000000000",
    "role:AI.Agent.Admin"
  ],
  "content": "..."
}
```

Supported values:

- `public` — available to authenticated and anonymous callers;
- `user:<object-id>` — one Entra user or service principal;
- `group:<object-id>` — members whose token contains that group;
- `role:<app-role>` — callers whose access token contains that role.

The indexer rejects missing, duplicate, malformed, or empty principal lists.
Group-overage tokens don't include the complete group list. In that case,
group-restricted documents remain unavailable; add Microsoft Graph overage
resolution only after reviewing its permissions, latency, and cache policy.

## Local validation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
npm install --no-audit --no-fund
npm run build
ruff check app scripts tests
pytest -q
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra init -backend=false
terraform -chdir=infra validate
```

Run `uvicorn app.main:app --reload`, then open `http://localhost:8000`.

## Next Phase 2 increments

1. Add a versioned evaluation dataset and quality/safety pipeline gate.
2. Add prompt-injection and sensitive-data adversarial cases.
3. Add dependency, Terraform, container, SBOM, and image-signing controls.
4. Add dashboards, SLOs, alerts, rollback, and index-recovery exercises.
5. Add private ingress, private ACR, WAF/APIM, and inspected egress only when
   enterprise requirements justify the cost.
