# Reproducing

## Requirements
Python 3.8+ standard library only. No pip installs, no GPU, no internet.

## Fast (seconds–minutes)
```bash
python3 src/tforge.py selftest
python3 src/transferforge.py run 1 11 300 && python3 src/transferforge.py report
python3 src/omniforge.py selftest
```

## Full batteries (hours, any CPU)
Use the Kaggle kernels in `experiments/kaggle/` (they self-slice and checkpoint),
or run the drivers directly, e.g.:
```bash
python3 src/rsi_upgrade.py xv2 101 140 99999 holdout   # compounding, n=40 holdout
python3 src/sdt_layer.py run 101 140 99999 holdout      # gate-integrity, n=40
python3 src/openforge.py run OPEN 1 5000 99999          # open-ended long run
```
Everything is deterministic in the seed and resumable from its state file.
