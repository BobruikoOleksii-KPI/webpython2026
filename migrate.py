from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import models
from database import SessionLocal as SQLiteSession
from database_postgres import SessionLocal as PostgresSession

print("Starting migration from SQLite to PostgreSQL...")

sqlite_db = SQLiteSession()
postgres_db = PostgresSession()

# Clear data in correct order
print("Clearing existing data in PostgreSQL...")
postgres_db.query(models.Loan).delete()
postgres_db.query(models.Book).delete()
postgres_db.query(models.Author).delete()
postgres_db.commit()

# === 1. Migrate Authors + create mapping ===
author_mapping = {}
authors = sqlite_db.query(models.Author).all()
for a in authors:
    new_a = models.Author(name=a.name, surname=a.surname, birth_year=a.birth_year)
    postgres_db.add(new_a)
    postgres_db.flush()                    # Force ID generation
    author_mapping[a.id] = new_a.id
postgres_db.commit()
print(f"Migrated {len(authors)} authors")

# === 2. Migrate Books + create mapping ===
book_mapping = {}
books = sqlite_db.query(models.Book).all()
for b in books:
    new_author_id = author_mapping.get(b.author_id)
    new_b = models.Book(
        title=b.title,
        year=b.year,
        author_id=new_author_id,
        available=b.available
    )
    postgres_db.add(new_b)
    postgres_db.flush()
    book_mapping[b.id] = new_b.id
postgres_db.commit()
print(f"Migrated {len(books)} books")

# === 3. Migrate Loans using new book_id ===
loans = sqlite_db.query(models.Loan).all()
for l in loans:
    new_book_id = book_mapping.get(l.book_id)
    if new_book_id is None:
        print(f"Warning: Book ID {l.book_id} not found, skipping loan")
        continue
    new_l = models.Loan(
        book_id=new_book_id,
        user_name=l.user_name,
        loan_date=l.loan_date,
        return_date=l.return_date
    )
    postgres_db.add(new_l)
postgres_db.commit()
print(f"Migrated {len(loans)} loans")

print("Migration completed successfully")

sqlite_db.close()
postgres_db.close()