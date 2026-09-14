.PHONY: demo serve test evaluate
PYTHON ?= python3
demo:
	$(PYTHON) -m scholar_compass demo
serve:
	$(PYTHON) -m scholar_compass serve
test:
	$(PYTHON) -m unittest discover -s tests -v
evaluate:
	$(PYTHON) -m evals.run
