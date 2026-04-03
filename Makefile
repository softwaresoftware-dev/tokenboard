.PHONY: test dev

test:
	python -m pytest tests/ -v

dev:
	claude --plugin-dir /home/thatcher/projects/nov/projects/plugins/apps/tokenboard
