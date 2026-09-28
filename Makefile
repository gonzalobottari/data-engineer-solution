.PHONY: start stop sync check dedupe dedupe-exec all clean demo-break demo-fix

# Start source database
start:
	docker compose up -d
	@echo "Waiting for database to be ready..."
	@sleep 3
	@docker compose exec source_db pg_isready -U fundo -d fundo_operational || (echo "Database not ready" && exit 1)
	@echo "Database is ready!"

# Stop database
stop:
	docker compose down

# Install Python dependencies
install:
	pip install -r pipeline/requirements.txt

# Run incremental sync
sync:
	cd pipeline && python run.py sync

# Run data quality checks
check:
	cd pipeline && python run.py check

# Analyze duplicates (dry run)
dedupe:
	cd pipeline && python run.py dedupe

# Execute duplicate merge
dedupe-exec:
	cd pipeline && python run.py dedupe-exec

# Run full pipeline: sync + checks
all:
	cd pipeline && python run.py all

# Clean warehouse data (reset)
clean:
	rm -rf warehouse/
	@echo "Warehouse cleaned"

# Demo: Break data to show failing checks
demo-break:
	@echo "Deleting a customer from source to simulate missing data..."
	docker compose exec source_db psql -U fundo -d fundo_operational -c "DELETE FROM customers WHERE id = 17;"
	@echo "Customer 17 deleted from source. Run 'make check' to see failing checks."

# Demo: Fix broken data
demo-fix:
	@echo "Restoring deleted customer..."
	docker compose exec source_db psql -U fundo -d fundo_operational -c "\
		INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) \
		VALUES (17, 'Chris', 'Martinez', 'chris.m@email.com', '555-890-1234', '333 Walnut Blvd, Atlanta, GA 30301', '012-34-5678', '2024-05-10 08:00:00', NOW());"
	@echo "Customer 17 restored. Run 'make sync' then 'make check' to verify."

# Full demo sequence
demo:
	@echo "=== FUNDO DATA PIPELINE DEMO ==="
	@echo ""
	@echo "1. Starting database..."
	@$(MAKE) start
	@echo ""
	@echo "2. Running initial sync..."
	@$(MAKE) sync
	@echo ""
	@echo "3. Running quality checks (should pass)..."
	@$(MAKE) check
	@echo ""
	@echo "4. Analyzing duplicates..."
	@$(MAKE) dedupe
