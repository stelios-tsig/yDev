# yDev

Μικρή πλατφόρμα όπου προγραμματιστές ανεβάζουν projects, τα κατηγοριοποιούν με
τεχνολογίες, και δέχονται σχόλια, βαθμολογίες και εκδόσεις (versions) από άλλους χρήστες.

## Στοίβα

- **FastAPI** + **Jinja2** templates (server-side rendering)
- **SQLAlchemy** + **Alembic** migrations, πάνω σε **PostgreSQL** (production, π.χ. Neon) με fallback σε τοπικό **SQLite** (`ydev.db`) όταν λείπει το `DATABASE_URL`
- Authentication με **JWT** σε httponly cookie
- **Cloudinary** για αποθήκευση εικόνων

## Εγκατάσταση

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env         # και συμπλήρωσε τις τιμές (SECRET_KEY, DATABASE_URL, Cloudinary)
alembic upgrade head         # δημιουργεί/ενημερώνει το schema της βάσης
```

## Εκτέλεση

```bash
uvicorn main:app --reload
```

Άνοιξε το `http://127.0.0.1:8000/home`.

## Tests

```bash
pytest
```

Τα tests ([`tests/`](tests/)) τρέχουν με FastAPI `TestClient` πάνω σε απομονωμένη
προσωρινή SQLite βάση (ορίζεται από το `tests/conftest.py` πριν φορτωθεί το app),
οπότε δεν αγγίζουν την πραγματική βάση ούτε το Cloudinary.

## Migrations (Alembic)

Το schema της βάσης το διαχειρίζεται αποκλειστικά το Alembic — το app δεν κάνει πλέον `create_all` στο startup.

```bash
alembic upgrade head                          # εφαρμόζει όλα τα εκκρεμή migrations
alembic revision --autogenerate -m "μήνυμα"   # δημιουργεί νέο migration μετά από αλλαγή σε models.py
alembic downgrade -1                          # αναιρεί το τελευταίο migration
alembic current                               # ποιο migration «βλέπει» η τρέχουσα βάση
```

> Σε μια βάση που ήδη έχει τους πίνακες (π.χ. δημιουργήθηκαν πριν μπει το Alembic) χρησιμοποίησε `alembic stamp head` αντί για `upgrade head`, ώστε να μην προσπαθήσει να ξαναδημιουργήσει ό,τι υπάρχει ήδη.

## Δομή

| Αρχείο | Ρόλος |
| --- | --- |
| `main.py` | Routes (JSON API + HTML σελίδες) |
| `models.py` | SQLAlchemy μοντέλα |
| `schemas.py` | Pydantic schemas |
| `auth_utils.py` | Hashing κωδικών, δημιουργία/έλεγχος JWT |
| `database.py` | Engine και session της βάσης |
| `cloud_utils.py` | Ανέβασμα εικόνων στο Cloudinary |
| `alembic/` | Migrations βάσης δεδομένων |
| `templates/` | Jinja2 templates |
| `static/` | CSS / JS |
| `tests/` | pytest suite (TestClient + SQLite) |

## Συμβάσεις URL

- **JSON API**: πληθυντικός, `/projects/{id}/comments/`, `/projects/{id}/ratings/`, `/projects/{id}/versions/`
- **HTML σελίδες**: ενικός, `/project/{id}/page`, `/project/{id}/edit`, `/project/{id}/delete`
