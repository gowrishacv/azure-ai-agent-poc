.PHONY: fmt validate test run

fmt:
	terraform -chdir=infra fmt -recursive

validate:
	terraform -chdir=infra init -backend=false
	terraform -chdir=infra validate

test:
	python -m pytest -q

run:
	uvicorn app.main:app --reload --port 8000

