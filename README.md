# Book-Recommendation-System
# 📚 Book Recommender System

A web app that recommends books using two approaches: a **popularity-based** ranking of the 50 top-rated books, and an **item-based collaborative filtering** model that suggests similar books based on user rating patterns. Built with Flask and scikit-learn, trained on the [Book-Crossing dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/).

## Features

- **Top 50 Books** — Home page showing the highest-rated books (with at least 250 ratings), sorted by average rating, complete with cover image, author, vote count, and rating.
- **Get Recommendations** — Search for a book you like and get 4 similar book recommendations based on collaborative filtering (cosine similarity over user rating vectors).

## Tech Stack

- **Backend:** Flask
- **Data processing / ML:** pandas, NumPy, scikit-learn (`cosine_similarity`)
- **Frontend:** Jinja2 templates + Bootstrap 3
- **Deployment:** Gunicorn (Heroku-style `Procfile` included)

## How It Works

The model is trained offline in [`book-recommender-system.ipynb`](book-recommender-system.ipynb) using three source CSVs (`books.csv`, `users.csv`, `ratings.csv` from the Book-Crossing dataset):

1. **Popularity-Based Recommender**
   Books are grouped by title to compute the number of ratings and average rating. Only books with **250+ ratings** are kept, sorted by average rating, and the top 50 are saved.

2. **Collaborative Filtering Recommender**
   - Only "power users" who rated more than 200 books are kept.
   - Only books with 50+ ratings (from these power users) are kept.
   - A user–item pivot table is built (`Book-Title` × `User-ID`, values = ratings, missing values filled with 0).
   - Cosine similarity is computed between every pair of books based on rating patterns.
   - For a given book, the 4 most similar books (by cosine similarity) are returned.

The trained artifacts (`popular.pkl`, `pt.pkl`, `books.pkl`, `similarity_scores.pkl`) are pre-computed and loaded directly by the Flask app at runtime — no retraining is needed to run the app.

## Project Structure

```
book-recommender-system-master/
├── app.py                          # Flask application
├── book-recommender-system.ipynb   # Data cleaning, EDA & model building
├── requirements.txt                # Python dependencies
├── Procfile                        # Process file for Heroku/Gunicorn deployment
├── popular.pkl                     # Top 50 books (precomputed)
├── pt.pkl                          # User–item pivot table
├── books.pkl                       # Cleaned books metadata
├── similarity_scores.pkl           # Cosine similarity matrix
└── templates/
    ├── index.html                  # Home page (top 50 books)
    └── recommend.html              # Recommendation search page
```

## Getting Started

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/<your-username>/book-recommender-system.git
   cd book-recommender-system
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app
   ```bash
   python app.py
   ```

4. Open your browser at `http://127.0.0.1:5000`

> The app loads the pre-trained `.pkl` files directly, so it runs without needing the original dataset or re-running the notebook.

## Usage

- Visit `/` to browse the top 50 books.
- Visit `/recommend` to search for a book and get similar recommendations.
- Note: the recommender expects an **exact book title match** (case-sensitive) from the underlying dataset, since it does an exact lookup against the pivot table index.

## Retraining the Model

If you want to rebuild the `.pkl` files from scratch:

1. Download the Book-Crossing dataset (`books.csv`, `users.csv`, `ratings.csv`) and place them in the project root.
2. Open and run [`book-recommender-system.ipynb`](book-recommender-system.ipynb) end to end.
3. This regenerates `popular.pkl`, `pt.pkl`, `books.pkl`, and `similarity_scores.pkl`.

## Deployment

This project includes a `Procfile` configured for Gunicorn, making it deployable on platforms like Heroku or Render out of the box:

```
web: gunicorn app:app
```

## Limitations

- Recommendations require an exact, case-sensitive title match — there's no fuzzy search or autocomplete yet.
- The collaborative filtering model only covers books/users that passed the rating-count thresholds during training, so very niche titles won't be available.
- `similarity_scores.pkl` is a dense cosine similarity matrix, so it doesn't scale well to very large catalogs.

## Future Improvements

- [ ] Add autocomplete/fuzzy search for book titles
- [ ] Add user-based (rather than item-based) collaborative filtering
- [ ] Add a search-as-you-type API endpoint
- [ ] Improve UI/UX with a modern frontend framework
- [ ] Add unit tests

## License

This project does not currently specify a license. Add one (e.g. MIT) if you plan to share or accept contributions.

## Acknowledgements

- [Book-Crossing Dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/) by Cai-Nicolas Ziegler
