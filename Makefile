.PHONY: test lint type-check fmt fmt-check validate plan deploy destroy

BLUEPRINT ?= synchronous-api
INFRA_DIR := infra/$(BLUEPRINT)
BLUEPRINTS := synchronous-api async-fanout orchestrated-workflow scheduled-batch
MODULES := iam_role idempotency_table dead_letter_queue lambda_function

# --- Python: handlers/shared, moto-backed, no AWS account needed ---

test:
	pip install -r requirements.txt > /dev/null
	pytest tests/ -q

lint:
	ruff check handlers tests

type-check:
	mypy handlers/shared --ignore-missing-imports

# --- Terraform: fmt/validate are credential-free and CI-checked.
#     plan/deploy/destroy touch a real AWS account and are NOT run in CI. ---

fmt:
	terraform fmt -recursive infra/

fmt-check:
	terraform fmt -check -recursive infra/

# Validates every blueprint root config and every shared module. No AWS
# credentials required: `terraform validate` only checks syntax/types
# against the provider schema, it never calls AWS.
validate:
	@for d in $(BLUEPRINTS); do \
		echo "=== infra/$$d ==="; \
		(cd infra/$$d && terraform init -backend=false -input=false > /dev/null && terraform validate) || exit 1; \
	done
	@for m in $(MODULES); do \
		echo "=== infra/modules/$$m ==="; \
		(cd infra/modules/$$m && terraform init -backend=false -input=false > /dev/null && terraform validate) || exit 1; \
	done

# plan/deploy/destroy require real AWS credentials (not available in this
# environment or in CI). BLUEPRINT selects which of the 4 root configs to
# target, e.g. `make deploy BLUEPRINT=async-fanout`.
plan:
	cd $(INFRA_DIR) && terraform init && terraform plan

deploy:
	cd $(INFRA_DIR) && terraform init && terraform apply

destroy:
	cd $(INFRA_DIR) && terraform init && terraform destroy
