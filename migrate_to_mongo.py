from sqlalchemy.orm import Session
import models
from database_postgres import SessionLocal as PostgresSession
from database_mongo import authors, books, loans
from datetime import datetime

print("Starting migration from PostgreSQL to MongoDB...")

postgres_db = PostgresSession()

# Clear old data
authors.delete_many({})
books.delete_many({})
loans.delete_many({})
print("Cleared old MongoDB data")

# === 1. Migrate Authors ===
pg_authors = postgres_db.query(models.Author).all()
for a in pg_authors:
    authors.insert_one({
        "_id": a.id,
        "name": a.name,
        "surname": a.surname,
        "birth_year": a.birth_year
    })
print(f"Migrated {len(pg_authors)} authors")

# === 2. Migrate Books ===
pg_books = postgres_db.query(models.Book).all()
for b in pg_books:
    books.insert_one({
        "_id": b.id,
        "title": b.title,
        "year": b.year,
        "author_id": b.author_id,
        "available": b.available
    })
print(f"Migrated {len(pg_books)} books")

# === 3. Migrate Loans (with date conversion) ===
pg_loans = postgres_db.query(models.Loan).all()
for l in pg_loans:
    # Convert datetime.date → datetime.datetime
    loan_date = datetime.combine(l.loan_date, datetime.min.time()) if l.loan_date else None
    return_date = datetime.combine(l.return_date, datetime.min.time()) if l.return_date else None

    loans.insert_one({
        "_id": l.id,
        "book_id": l.book_id,
        "user_name": l.user_name,
        "loan_date": loan_date,
        "return_date": return_date
    })
print(f"Migrated {len(pg_loans)} loans")

print("Migration to MongoDB completed successfully")

postgres_db.close()