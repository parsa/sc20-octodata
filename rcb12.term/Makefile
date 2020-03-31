#!/usr/bin/env make -f
.PHONY: all
all: run

.PHONY: run
run:
	python3 -m rcb12_term

.PHONY: tests
tests:
	-python3 -m unittest discover tests/ -v

.PHONY: clean
clean:
	-rm -rf build dist *.egg-info
	-find . -name '__pycache__' -type d -delete
	-find . -name '*.pyc' -type f -delete
