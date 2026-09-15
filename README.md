# yDev

*[Ελληνικά](#ydev--ελληνικά) · [English](#ydev--english)*

<a id="ydev--ελληνικά"></a>

## yDev — Ελληνικά

Μικρή πλατφόρμα όπου προγραμματιστές ανεβάζουν projects, τα κατηγοριοποιούν με
τεχνολογίες, και δέχονται σχόλια, βαθμολογίες και εκδόσεις (versions) από άλλους χρήστες.

### Στοίβα

- **FastAPI** + **Jinja2** templates (server-side rendering)
- **SQLAlchemy** + **Alembic** migrations, πάνω σε **PostgreSQL** (production, π.χ. Neon) με fallback σε τοπικό **SQLite** (`ydev.db`) όταν λείπει το `DATABASE_URL`
- Authentication με **JWT** σε httponly cookie· επαναφορά κωδικού μέσω email (SMTP)
- **Cloudinary** για αποθήκευση εικόνων

### Εγκατάσταση

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env         # και συμπλήρωσε τις τιμές (SECRET_KEY, DATABASE_URL, Cloudinary)
alembic upgrade head         # δημιουργεί/ενημερώνει το schema της βάσης
```

### Εκτέλεση

```bash
uvicorn main:app --reload
```

Άνοιξε το `http://127.0.0.1:8000/home`.

### Tests

```bash
pytest
```

Τα tests ([`tests/`](tests/)) τρέχουν με FastAPI `TestClient` πάνω σε απομονωμένη
προσωρινή SQLite βάση (ορίζεται από το `tests/conftest.py` πριν φορτωθεί το app),
οπότε δεν αγγίζουν την πραγματική βάση ούτε το Cloudinary.

### Migrations (Alembic)

Το schema της βάσης το διαχειρίζεται αποκλειστικά το Alembic — το app δεν κάνει πλέον `create_all` στο startup.

```bash
alembic upgrade head                          # εφαρμόζει όλα τα εκκρεμή migrations
alembic revision --autogenerate -m "μήνυμα"   # δημιουργεί νέο migration μετά από αλλαγή σε models.py
alembic downgrade -1                          # αναιρεί το τελευταίο migration
alembic current                               # ποιο migration «βλέπει» η τρέχουσα βάση
```

> Σε μια βάση που ήδη έχει τους πίνακες (π.χ. δημιουργήθηκαν πριν μπει το Alembic) χρησιμοποίησε `alembic stamp head` αντί για `upgrade head`, ώστε να μην προσπαθήσει να ξαναδημιουργήσει ό,τι υπάρχει ήδη.

### Deploy (Render)

Το [`render.yaml`](render.yaml) είναι έτοιμο Blueprint. Στο Render: **New + → Blueprint →**
διάλεξε αυτό το repo. Το build τρέχει `pip install -r requirements.txt && alembic upgrade head`
και το app ξεκινά με `uvicorn main:app --host 0.0.0.0 --port $PORT`.

Πριν το πρώτο deploy όρισε στο **Environment**: `DATABASE_URL` (Neon), `CLOUDINARY_*`
και `RESEND_API_KEY`. Το `SECRET_KEY` δημιουργείται αυτόματα. Η έκδοση Python ορίζεται
στο [`.python-version`](.python-version).

Το Render μπλοκάρει το εξερχόμενο SMTP, οπότε τα emails φεύγουν μέσω **Resend**
(HTTP API). Τοπικά μπορείς να χρησιμοποιήσεις είτε `RESEND_API_KEY` είτε `SMTP_*`
(π.χ. Gmail app password) — δες [`.env.example`](.env.example).

> **Παράδοση email (demo):** το Resend, χωρίς verified domain, στέλνει μόνο στη
> διεύθυνση του ιδιοκτήτη του λογαριασμού. Στο deployed demo, ο σύνδεσμος
> επαναφοράς κωδικού γράφεται στα logs του Render αντί να σταλεί email. Για
> κανονική παράδοση σε οποιονδήποτε χρήστη χρειάζεται domain επιβεβαιωμένο στο
> Resend και `EMAIL_FROM=noreply@to-domain-sou.com`.

> Το `DATABASE_URL` πρέπει να είναι σκέτο connection string που ξεκινά με
> `postgresql://` — όχι η εντολή `psql '...'` που δείχνει το Neon, ούτε με εισαγωγικά.

### Δομή

| Αρχείο | Ρόλος |
| --- | --- |
| `main.py` | Routes (JSON API + HTML σελίδες) |
| `models.py` | SQLAlchemy μοντέλα |
| `schemas.py` | Pydantic schemas |
| `auth_utils.py` | Hashing κωδικών, δημιουργία/έλεγχος JWT |
| `email_utils.py` | Αποστολή email (Resend > SMTP > console) |
| `rate_limit.py` | In-memory rate limiting στα auth endpoints |
| `database.py` | Engine και session της βάσης |
| `cloud_utils.py` | Ανέβασμα εικόνων στο Cloudinary |
| `alembic/` | Migrations βάσης δεδομένων |
| `templates/` | Jinja2 templates |
| `static/` | CSS / JS |
| `tests/` | pytest suite (TestClient + SQLite) |

### Συμβάσεις URL

- **JSON API**: πληθυντικός, `/projects/{id}/comments/`, `/projects/{id}/ratings/`, `/projects/{id}/versions/`
- **HTML σελίδες**: ενικός, `/project/{id}/page`, `/project/{id}/edit`, `/project/{id}/delete`

---

<a id="ydev--english"></a>

## yDev — English

A small platform where developers upload projects, categorise them by
technology, and receive comments, ratings and versions from other users.

### Stack

- **FastAPI** + **Jinja2** templates (server-side rendering)
- **SQLAlchemy** + **Alembic** migrations, on top of **PostgreSQL** (production, e.g. Neon) with a fallback to a local **SQLite** file (`ydev.db`) when `DATABASE_URL` is not set
- Authentication with **JWT** in an httponly cookie; password reset via email (SMTP)
- **Cloudinary** for image storage

### Installation

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env         # then fill in the values (SECRET_KEY, DATABASE_URL, Cloudinary)
alembic upgrade head         # creates/updates the database schema
```

### Running

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/home`.

### Tests

```bash
pytest
```

The tests ([`tests/`](tests/)) run with the FastAPI `TestClient` against an isolated
temporary SQLite database (configured by `tests/conftest.py` before the app is imported),
so they never touch the real database or Cloudinary.

### Migrations (Alembic)

The database schema is managed exclusively by Alembic — the app no longer calls `create_all` on startup.

```bash
alembic upgrade head                          # applies all pending migrations
alembic revision --autogenerate -m "message"  # creates a new migration after changing models.py
alembic downgrade -1                          # reverts the last migration
alembic current                               # shows which migration the current database is at
```

> On a database that already has the tables (e.g. created before Alembic was introduced), use `alembic stamp head` instead of `upgrade head`, so it does not try to recreate what already exists.

### Deploy (Render)

[`render.yaml`](render.yaml) is a ready-to-use Blueprint. In Render: **New + → Blueprint →**
pick this repo. The build runs `pip install -r requirements.txt && alembic upgrade head`
and the app starts with `uvicorn main:app --host 0.0.0.0 --port $PORT`.

Before the first deploy, set under **Environment**: `DATABASE_URL` (Neon), `CLOUDINARY_*`
and `RESEND_API_KEY`. `SECRET_KEY` is generated automatically. The Python version is
pinned in [`.python-version`](.python-version).

Render blocks outbound SMTP, so emails are sent through **Resend** (HTTP API).
Locally you can use either `RESEND_API_KEY` or `SMTP_*` (e.g. a Gmail app password)
— see [`.env.example`](.env.example).

> **Email delivery (demo):** without a verified domain, Resend only delivers to the
> account owner's address. In the deployed demo, the password reset link is written
> to the Render logs instead of being emailed. Real delivery to any user requires a
> domain verified with Resend and `EMAIL_FROM=noreply@your-domain.com`.

> `DATABASE_URL` must be a plain connection string starting with `postgresql://` —
> not the `psql '...'` command that Neon shows, and not wrapped in quotes.

### Structure

| File | Role |
| --- | --- |
| `main.py` | Routes (JSON API + HTML pages) |
| `models.py` | SQLAlchemy models |
| `schemas.py` | Pydantic schemas |
| `auth_utils.py` | Password hashing, JWT creation/verification |
| `email_utils.py` | Sending email (Resend > SMTP > console) |
| `rate_limit.py` | In-memory rate limiting on the auth endpoints |
| `database.py` | Database engine and session |
| `cloud_utils.py` | Image uploads to Cloudinary |
| `alembic/` | Database migrations |
| `templates/` | Jinja2 templates |
| `static/` | CSS / JS |
| `tests/` | pytest suite (TestClient + SQLite) |

### URL conventions

- **JSON API**: plural, `/projects/{id}/comments/`, `/projects/{id}/ratings/`, `/projects/{id}/versions/`
- **HTML pages**: singular, `/project/{id}/page`, `/project/{id}/edit`, `/project/{id}/delete`
