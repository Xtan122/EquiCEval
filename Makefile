.PHONY: all help pdf all-pdf papers docs slides clean test benchmark reproduce list

PYTHON ?= python3

help:
	@echo "========================================================================"
	@echo "                      EquiCEval Build & Task Runner"
	@echo "========================================================================"
	@echo "Document Commands:"
	@echo "  make pdf         - Compile all LaTeX documents to output/pdf/"
	@echo "  make papers      - Compile research papers (equiceval & trustworthy)"
	@echo "  make docs        - Compile onboarding lab guides & Q&A notes"
	@echo "  make slides      - Compile Beamer presentation slides"
	@echo "  make list        - List all registered document build targets"
	@echo "  make clean       - Clean all temporary build artifacts & aux files"
	@echo ""
	@echo "Benchmark & Research Pipeline:"
	@echo "  make test        - Run unit test suite (16 tests)"
	@echo "  make benchmark   - Run full 1,200 evaluation benchmark"
	@echo "  make reproduce   - Execute end-to-end reproduction pipeline"
	@echo "========================================================================"

pdf:
	$(PYTHON) scripts/compile_latex.py --all

all-pdf: pdf

papers:
	$(PYTHON) scripts/compile_latex.py --target papers

docs:
	$(PYTHON) scripts/compile_latex.py --target docs

slides:
	$(PYTHON) scripts/compile_latex.py --target slides

list:
	$(PYTHON) scripts/compile_latex.py --list

clean:
	$(PYTHON) scripts/compile_latex.py --clean

test:
	$(PYTHON) cli.py test

benchmark:
	$(PYTHON) cli.py run-benchmark

reproduce:
	$(PYTHON) cli.py full-reproduce
