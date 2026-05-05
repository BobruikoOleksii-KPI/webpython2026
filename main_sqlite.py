from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine
from models import Base, Book, Author, Loan
from datetime import date

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Library Management System",
    description="Лабораторна робота №1. FastAPI + SQLAlchemy ORM",
    version="1.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def create_sample_data():
    db = SessionLocal()
    if db.query(Author).count() == 0:
        # Sample authors
        author1 = Author(name="Іван", surname="Франко", birth_year=1856)
        author2 = Author(name="Леся", surname="Українка", birth_year=1871)
        db.add_all([author1, author2])
        db.commit()
        
        # Sample books
        book1 = Book(title="Захар Беркут", year=1883, author_id=author1.id)
        book2 = Book(title="Лісова пісня", year=1911, author_id=author2.id)
        db.add_all([book1, book2])
        db.commit()
    db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(role: str = "user"):
    html = f"""
    <h1>Бібліотека</h1>
    <p><b>Поточний режим:</b> {role.upper()}</p>
    <p>
        <a href="/?role=admin">Увійти як Адміністратор</a> | 
        <a href="/?role=user">Увійти як Користувач</a>
    </p>
    <hr>
    <p><a href="/books?role={role}">Переглянути всі книги</a></p>
    <p><a href="/docs">Документація OpenAPI</a></p>
    <p><a href="/stats">Статистика</a></p>
    """
    return HTMLResponse(content=html)

@app.get("/books", response_class=HTMLResponse)
async def list_books(role: str = "user", db: Session = Depends(get_db)):
    books = db.query(Book).all()
    
    html = f"<h1>Список книг (Режим: {role.upper()})</h1>"
    html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th>ID</th><th>Назва</th><th>Рік</th><th>Автор</th><th>Статус</th><th>Дії</th></tr>"
    
    for book in books:
        author_name = f"{book.author.name} {book.author.surname}" if book.author else "Невідомий"
        status = "Доступна" if book.available else "Видана"
        
        actions = ""
        if role == "admin":
            actions += f"<a href='/books/{book.id}/edit?role=admin'>Редагувати</a> | "
            actions += f"<a href='/books/{book.id}/delete?role=admin' onclick=\"return confirm('Видалити книгу?')\">Видалити</a>"
            if not book.available:
                actions += f" | <a href='/books/{book.id}/return?role=admin' onclick=\"return confirm('Повернути книгу?')\">Повернути</a>"
        else:
            if book.available:
                actions += f"<a href='/books/{book.id}/borrow?role=user'>Позичити</a>"
        
        html += f"""
        <tr>
            <td>{book.id}</td>
            <td>{book.title}</td>
            <td>{book.year}</td>
            <td>{author_name}</td>
            <td>{status}</td>
            <td>{actions}</td>
        </tr>"""
    
    html += "</table><br>"
    if role == "admin":
        html += "<a href='/books/add?role=admin'>Додати нову книгу</a> | "
    html += f"<a href='/?role={role}'>← На головну</a>"
    return HTMLResponse(content=html)

@app.get("/books/add", response_class=HTMLResponse)
async def add_book_form(role: str = "user"):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    html = """
    <h1>Додати нову книгу</h1>
    <form action="/books" method="post">
        <p>Назва: <input type="text" name="title" required></p>
        <p>Рік видання: <input type="number" name="year" required></p>
        <p>Автор ID (1 або 2): <input type="number" name="author_id" value="1" required></p>
        <button type="submit">Додати книгу</button>
    </form>
    <br><a href="/books?role=admin">← Назад до списку</a>
    """
    return HTMLResponse(content=html)

@app.post("/books")
async def create_book(title: str = Form(...), year: int = Form(...), author_id: int = Form(...),
                      role: str = "user", db: Session = Depends(get_db)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    new_book = Book(title=title, year=year, author_id=author_id)
    db.add(new_book)
    db.commit()
    return RedirectResponse(url="/books?role=admin", status_code=303)

@app.get("/books/{book_id}/edit", response_class=HTMLResponse)
async def edit_book_form(book_id: int, role: str = "user", db: Session = Depends(get_db)):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не знайдена")
    
    html = f"""
    <h1>Редагувати книгу</h1>
    <form action="/books/{book_id}/update" method="post">
        <p>Назва: <input type="text" name="title" value="{book.title}" required></p>
        <p>Рік видання: <input type="number" name="year" value="{book.year}" required></p>
        <p>Автор ID: <input type="number" name="author_id" value="{book.author_id}" required></p>
        <button type="submit">Зберегти зміни</button>
    </form>
    <br><a href="/books?role=admin">← Назад до списку</a>
    """
    return HTMLResponse(content=html)

@app.post("/books/{book_id}/update")
async def update_book(book_id: int, title: str = Form(...), year: int = Form(...), 
                      author_id: int = Form(...), role: str = "user", db: Session = Depends(get_db)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не знайдена")
    
    book.title = title
    book.year = year
    book.author_id = author_id
    db.commit()
    return RedirectResponse(url="/books?role=admin", status_code=303)

@app.get("/books/{book_id}/delete")
async def delete_book(book_id: int, role: str = "user", db: Session = Depends(get_db)):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    book = db.query(Book).filter(Book.id == book_id).first()
    if book:
        db.delete(book)
        db.commit()
    return RedirectResponse(url="/books?role=admin", status_code=303)

@app.get("/books/{book_id}/borrow")
async def borrow_book(book_id: int, role: str = "user", db: Session = Depends(get_db)):
    if role != "user":
        return RedirectResponse(url="/books?role=user")
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book or not book.available:
        raise HTTPException(status_code=400, detail="Книга недоступна для видачі")
    
    loan = Loan(book_id=book.id, user_name="Тестовий Користувач", loan_date=date.today())
    book.available = False
    db.add(loan)
    db.commit()
    return RedirectResponse(url=f"/books?role=user", status_code=303)

@app.get("/books/{book_id}/return")
async def return_book(book_id: int, role: str = "user", db: Session = Depends(get_db)):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    
    book = db.query(Book).filter(Book.id == book_id).first()
    if book:
        book.available = True
        latest_loan = db.query(Loan)\
            .filter(Loan.book_id == book_id)\
            .order_by(Loan.loan_date.desc())\
            .first()
        if latest_loan and not latest_loan.return_date:
            latest_loan.return_date = date.today()
        db.commit()
    
    return RedirectResponse(url=f"/books?role=admin", status_code=303)