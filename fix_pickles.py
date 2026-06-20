"""
Fix pickle files created with old pandas (1.x) for use with modern pandas (2.x+).
Patches several removed/renamed modules and internal API changes.
"""
import pickle
import sys
import types
import pandas as pd
import pandas.core.indexes
import numpy as np

# ── Shim 1: pandas.core.indexes.numeric (removed in pandas 2.0) ──────────────
numeric_shim = types.ModuleType("pandas.core.indexes.numeric")
numeric_shim.Int64Index   = pd.Index
numeric_shim.Float64Index = pd.Index
numeric_shim.UInt64Index  = pd.Index
sys.modules.setdefault("pandas.core.indexes.numeric", numeric_shim)

# ── Shim 2: pandas.core.indexes.base – patch any missing attrs ───────────────
import pandas.core.indexes.base as _idx_base
if not hasattr(_idx_base, "Int64Index"):
    _idx_base.Int64Index   = pd.Index
if not hasattr(_idx_base, "Float64Index"):
    _idx_base.Float64Index = pd.Index
if not hasattr(_idx_base, "UInt64Index"):
    _idx_base.UInt64Index  = pd.Index

# ── Shim 3: new_block placement fix (slice → BlockPlacement) ─────────────────
import pandas.core.internals.blocks as _blocks
from pandas._libs.internals import BlockPlacement as _BP

_orig_new_block = _blocks.new_block

def _patched_new_block(values, placement, ndim=None, refs=None):
    if isinstance(placement, slice):
        placement = _BP(placement)
    if ndim is not None:
        return _orig_new_block(values, placement, ndim=ndim, refs=refs)
    return _orig_new_block(values, placement, refs=refs)

_blocks.new_block = _patched_new_block

# ─────────────────────────────────────────────────────────────────────────────

def load_and_fix(filepath):
    with open(filepath, "rb") as f:
        return pickle.load(f)

print("Attempting to load and re-save pickle files...")

files = ["popular.pkl", "pt.pkl", "books.pkl", "similarity_scores.pkl"]

for fname in files:
    print(f"Processing {fname} ...", end=" ", flush=True)
    try:
        obj = load_and_fix(fname)
        print(f"loaded ({type(obj).__name__})", end=" ", flush=True)
        with open(fname, "wb") as f:
            pickle.dump(obj, f)
        print("-> re-saved OK")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

print("\nAll pickle files fixed! You can now run:  py -3 app.py")
