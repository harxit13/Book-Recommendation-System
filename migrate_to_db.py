"""
migrate_to_db.py
One-time script: reads existing .pkl files and populates the SQLite database.
Run once:  py -3 migrate_to_db.py
"""

import sys, types
import pandas as pd
import numpy as np

# ── pandas 1.x pickle compatibility shims ────────────────────────────────────
numeric_shim = types.ModuleType("pandas.core.indexes.numeric")
numeric_shim.Int64Index   = pd.Index
numeric_shim.Float64Index = pd.Index
numeric_shim.UInt64Index  = pd.Index
sys.modules.setdefault("pandas.core.indexes.numeric", numeric_shim)

import pandas.core.internals.blocks as _blocks
from pandas._libs.internals import BlockPlacement as _BP
_orig = _blocks.new_block
def _patched(values, placement, ndim=None, refs=None):
    if isinstance(placement, slice): placement = _BP(placement)
    return _orig(values, placement, ndim=ndim, refs=refs) if ndim else _orig(values, placement, refs=refs)
_blocks.new_block = _patched
# ─────────────────────────────────────────────────────────────────────────────

import pickle
from database import init_db, insert_popular_books, insert_books, is_populated

def load_pkl(path):
    with open(path, "rb") as f:
        return pickle.load(f)

print("Initialising database schema...")
init_db()

if is_populated():
    print("Database already populated. Nothing to do.")
    sys.exit(0)

# ── Popular books ─────────────────────────────────────────────────────────────
print("Loading popular.pkl ...")
pop = load_pkl("popular.pkl")
pop_rows = list(zip(
    pop["Book-Title"].astype(str),
    pop["Book-Author"].astype(str),
    pop["Image-URL-M"].astype(str),
    pop["num_ratings"].astype(int),
    pop["avg_rating"].astype(float).round(2),
))
insert_popular_books(pop_rows)

# ── Full book catalog ─────────────────────────────────────────────────────────
print("Loading books.pkl (this may take a moment) ...")
books = load_pkl("books.pkl")

# normalise column names – handle both old and new pickle formats
books.columns = [c.strip() for c in books.columns]
col_map = {
    "ISBN": "isbn", "Book-Title": "title", "Book-Author": "author",
    "Year-Of-Publication": "year", "Publisher": "publisher",
    "Image-URL-S": "image_s", "Image-URL-M": "image_m", "Image-URL-L": "image_l",
}
books = books.rename(columns=col_map)

# keep only needed columns (fill missing ones)
for col in ["isbn","title","author","year","publisher","image_s","image_m","image_l"]:
    if col not in books.columns:
        books[col] = ""

books = books[["isbn","title","author","year","publisher","image_s","image_m","image_l"]]
books = books.drop_duplicates(subset=["title"])
books = books.fillna("")

# convert year to int safely
def safe_int(v):
    try: return int(v)
    except: return 0

book_rows = [
    (str(r.isbn), str(r.title), str(r.author),
     safe_int(r.year), str(r.publisher),
     str(r.image_s), str(r.image_m), str(r.image_l))
    for r in books.itertuples(index=False)
]
insert_books(book_rows)

print(f"\nMigration complete!")
print(f"  Popular books : {len(pop_rows)}")
print(f"  Book catalog  : {len(book_rows)}")
print(f"\nYou can now run:  py -3 app.py")
