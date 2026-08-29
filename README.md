# yDev

Μικρή πλατφόρμα όπου προγραμματιστές ανεβάζουν projects, τα κατηγοριοποιούν με
τεχνολογίες, και δέχονται σχόλια, βαθμολογίες και εκδόσεις (versions) από άλλους χρήστες.

## Στοίβα

- **FastAPI** + **Jinja2** templates (server-side rendering)
- **SQLAlchemy** πάνω σε **SQLite** (`ydev.db`)
- Authentication με **JWT** σε httponly cookie
- **Cloudinary** για αποθήκευση εικόνων

## Εγκατάσταση

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env         # και συμπλήρωσε τις τιμές
```

## Εκτέλεση

```bash
uvicorn main:app --reload
```

Άνοιξε το `http://127.0.0.1:8000/home`.

## Δομή

| Αρχείο | Ρόλος |
| --- | --- |
| `main.py` | Routes (JSON API + HTML σελίδες) |
| `models.py` | SQLAlchemy μοντέλα |
| `schemas.py` | Pydantic schemas |
| `auth_utils.py` | Hashing κωδικών, δημιουργία/έλεγχος JWT |
| `database.py` | Engine και session της βάσης |
| `cloud_utils.py` | Ανέβασμα εικόνων στο Cloudinary |
| `templates/` | Jinja2 templates |
| `static/` | CSS |

## Συμβάσεις URL

- **JSON API**: πληθυντικός, `/projects/{id}/comments/`, `/projects/{id}/ratings/`, `/projects/{id}/versions/`
- **HTML σελίδες**: ενικός, `/project/{id}/page`, `/project/{id}/edit`, `/project/{id}/delete`
