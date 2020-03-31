#!/usr/bin/env make -f
.PHONY: all
all: run

.PHONY: run
run:
	python3 -m rcb12_term

.PHONY: profile_runtime
profile_runtime:
	python3 -mcProfile -o rcb12_term_runtime.prof -m rcb12_term
	! tuna rcb12_term_runtime.prof

.PHONY: profile_imports
profile_imports:
	python3 -X importtime -m rcb12_term 2>rcb12_term_import.prof
	! tuna rcb12_term_import.prof

.PHONY: tests
tests:
	-python3 -m unittest discover tests/ -v

.PHONY: checks
checks:
	python3 -m checks

.PHONY: clean
clean:
	-rm -rf build dist *.egg-info
	-find . -name '__pycache__' -type d -delete
	-find . -name '*.pyc' -type f -delete
