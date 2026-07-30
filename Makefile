.PHONY: test dev

test:
	python -m pytest tests/ -v

dev:
	claude --plugin-dir $(CURDIR)
