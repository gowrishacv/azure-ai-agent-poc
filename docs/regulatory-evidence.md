# GDPR/DORA regulatory-evidence stage

The Azure DevOps `RegulatoryEvidence` stage runs after Terraform apply and
before the application build/deployment. This placement lets the stage use the
newly deployed Microsoft Foundry chat model through workload identity
federation.

The stage has two deliberately separate responsibilities:

1. Deterministic checks inspect version-controlled infrastructure and policy
   evidence. Critical failures block deployment.
2. Microsoft Foundry receives only the sanitized check results and produces an
   advisory gap summary. Source code, Terraform state, secrets, prompts, and
   customer data are not sent for this review.

The pipeline publishes:

- `regulatory-report.md` for reviewers;
- `regulatory-report.json` for automation;
- `evidence-manifest.json` with evidence paths and SHA-256 hashes.

The report is not legal advice, a certification, or proof of compliance.
GDPR applicability, DPIA decisions, DORA applicability, risk acceptance, and
approval remain human responsibilities. DORA is a financial-sector regulation;
an authorised owner must determine whether the organisation and workload are
in scope.

Initial mappings:

- GDPR Articles 25, 32, and 35;
- DORA Articles 9, 10, and 11.

The source mappings link directly to the official EUR-Lex texts. Review the
control definitions in `compliance/controls/` with legal, privacy, security,
and operational owners before using them outside this POC.

Run deterministic checks locally:

```bash
python scripts/regulatory_evidence.py \
  --repository-root . \
  --output-dir .artifacts/regulatory-evidence \
  --fail-on-critical
```

The local command does not call AI unless `--ai` is explicitly supplied and
the Foundry environment variables plus Azure CLI authentication are available.

## Safe personal-data detection demonstration

The evidence scanner can inspect repository files for potential personal-data
indicators before any AI call. It reports only the file path, SHA-256 digest,
indicator categories, and counts. Matched values are never copied into the
Markdown or JSON evidence artifacts and are never sent to Microsoft Foundry.

Use only the included reserved synthetic values:

```bash
python scripts/regulatory_evidence.py \
  --repository-root . \
  --output-dir .artifacts/pii-demo \
  --pii-scan-path tests/fixtures/synthetic-personal-data.txt
```

The report should show five indicators: a labelled person name, email address,
international phone number, documentation-range IPv4 address, and synthetic
customer identifier. All matches require human validation because pattern
detection can produce false positives.

The Azure DevOps regulatory stage scans `data/` with
`--fail-on-personal-data`. Do not add the synthetic fixture to `data/`, because
that would intentionally block deployment.

## Visio reference design

- [Platform architecture SVG](diagrams/azure-ai-agent-platform-visio-reference.svg)
- [Regulatory delivery flow SVG](diagrams/azure-devops-regulatory-flow-visio-reference.svg)
- [Visio build guide](diagrams/visio-build-guide.md)
