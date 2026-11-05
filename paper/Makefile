TECTONIC ?= tectonic
TECTONIC_FLAGS ?= --keep-logs --keep-intermediates -b https://data1.fullyjustified.net/tlextras-2022.0r0.tar
PYTHON ?= python

.PHONY: all build analyze
all: build

build:
	$(TECTONIC) $(TECTONIC_FLAGS) main.tex

# Optional: requires the historical artifact beside this paper directory.
analyze:
	$(PYTHON) ../historical_analysis/scripts/22_camera_ready.py
	cp ../historical_analysis/results/camera_ready/tables/*.tex generated/tables/
	cp ../historical_analysis/results/camera_ready/figures/*.pdf generated/figures/
