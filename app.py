from flask import Flask, render_template, request, jsonify
import pickle
import numpy as np
from database import (
    init_db, is_populated,
    get_popular_books, get_book_by_title, search_books,
    log_search, get_recent_searches, get_search_stats,
    add_feedback, get_feedback_for_book, get_avg_feedback, get_top_rated_feedback,
)

# ── Load ML model assets (still pkl – matrices aren't suited for SQL) ─────────
pt                = pickle.load(open('pt.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))
books_df          = pickle.load(open('books.pkl', 'rb'))   # for title→image lookup

# ── Database bootstrap ────────────────────────────────────────────────────────
init_db()
if not is_populated():
    # Auto-migrate on first run
    import migrate_to_db  # noqa: F401  (runs the migration as a side-effect)

app = Flask(__name__)


# ── Home – Top 50 books from DB ───────────────────────────────────────────────
@app.route('/')
def index():
    rows = get_popular_books()
    return render_template('index.html',
                           book_name=[r['title']       for r in rows],
                           author   =[r['author']      for r in rows],
                           image    =[r['image_url']   for r in rows],
                           votes    =[r['num_ratings'] for r in rows],
                           rating   =[r['avg_rating']  for r in rows])


# ── Recommend page ────────────────────────────────────────────────────────────
@app.route('/recommend')
def recommend_ui():
    recent = get_recent_searches(10)
    top_rated = get_top_rated_feedback(5)
    return render_template('recommend.html',
                           data=None,
                           recent=recent,
                           top_rated=top_rated)


@app.route('/recommend_books', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input', '').strip()
    data = []
    error = None

    try:
        idx = np.where(pt.index == user_input)[0]
        if len(idx) == 0:
            raise ValueError(f'Book not found in model: "{user_input}"')

        similar_items = sorted(
            enumerate(similarity_scores[idx[0]]),
            key=lambda x: x[1], reverse=True
        )[1:6]  # top 5

        for i, _score in similar_items:
            book_title = pt.index[i]
            # Try DB first, fall back to pkl
            db_row = get_book_by_title(book_title)
            if db_row:
                avg, cnt = get_avg_feedback(book_title)
                data.append({
                    'title':  db_row['title'],
                    'author': db_row['author'],
                    'image':  db_row['image_m'],
                    'avg_rating': avg,
                    'rating_count': cnt,
                })
            else:
                temp = books_df[books_df['Book-Title'] == book_title]
                if not temp.empty:
                    row = temp.drop_duplicates('Book-Title').iloc[0]
                    data.append({
                        'title':  row['Book-Title'],
                        'author': row['Book-Author'],
                        'image':  row['Image-URL-M'],
                        'avg_rating': None,
                        'rating_count': 0,
                    })

    except ValueError as e:
        error = str(e)

    # Log every search (even failed ones)
    log_search(user_input, len(data))

    recent    = get_recent_searches(10)
    top_rated = get_top_rated_feedback(5)
    return render_template('recommend.html',
                           data=data,
                           query=user_input,
                           error=error,
                           recent=recent,
                           top_rated=top_rated)


# ── Book detail page ──────────────────────────────────────────────────────────
@app.route('/book/<path:title>')
def book_detail(title):
    db_row   = get_book_by_title(title)
    feedback = get_feedback_for_book(title)
    avg, cnt = get_avg_feedback(title)
    return render_template('book_detail.html',
                           book=db_row,
                           title=title,
                           feedback=feedback,
                           avg_rating=avg,
                           rating_count=cnt)


# ── Submit feedback (AJAX + form) ─────────────────────────────────────────────
@app.route('/feedback', methods=['POST'])
def submit_feedback():
    book_title = request.form.get('book_title', '').strip()
    stars      = int(request.form.get('stars', 0))
    comment    = request.form.get('comment', '').strip()
    if book_title and 1 <= stars <= 5:
        add_feedback(book_title, stars, comment)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            avg, cnt = get_avg_feedback(book_title)
            return jsonify(success=True, avg=avg, cnt=cnt)
    return jsonify(success=False)


# ── Search autocomplete ───────────────────────────────────────────────────────
@app.route('/autocomplete')
def autocomplete():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = search_books(q, limit=8)
    return jsonify([{'title': r['title'], 'author': r['author']} for r in results])


# ── Search history page ───────────────────────────────────────────────────────
@app.route('/history')
def history():
    recent = get_recent_searches(50)
    total, top = get_search_stats()
    return render_template('history.html', recent=recent, total=total, top=top)


if __name__ == '__main__':
    app.run(debug=True)