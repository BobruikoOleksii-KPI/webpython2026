from fastapi import FastAPI, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
from database_mongo import authors, books, loans

app = FastAPI(
    title="Library Management System - MongoDB",
    version="1.0"
)

@app.get("/", response_class=HTMLResponse)
async def read_root(role: str = "user"):
    html = f"""
    <h1>Бібліотека (MongoDB)</h1>
    <p><b>Поточний режим:</b> {role.upper()}</p>
    <p>
        <a href="/?role=admin">Адміністратор</a> | 
        <a href="/?role=user">Користувач</a>
    </p>
    <hr>
    <p><a href="/books?role={role}">Переглянути всі книги</a></p>
    <p><a href="/search?role={role}">Пошук книг</a></p>
    <p><a href="/stats">Статистика</a></p>
    """
    return HTMLResponse(content=html)

# ====================== SEARCH (FINAL FIXED VERSION) ======================
@app.get("/search", response_class=HTMLResponse)
async def search_books(q: str = Query("", alias="q"), role: str = "user"):
    html = f"<h1>Пошук книг (Режим: {role.upper()})</h1>"
    html += f"""
    <form method="get">
        <p><input type="text" name="q" placeholder="Назва книги або автор..." style="width:400px" value="{q}"></p>
        <button type="submit">Шукати</button>
    </form><br>
    """

    if q.strip():
        query = q.strip()

        # 1. Find authors whose name OR surname contains any word from the query
        words = query.split()
        author_query = {"$or": []}
        for word in words:
            author_query["$or"].extend([
                {"name": {"$regex": word, "$options": "i"}},
                {"surname": {"$regex": word, "$options": "i"}}
            ])

        matching_authors = list(authors.find(author_query))
        author_ids = [a["_id"] for a in matching_authors]

        # 2. Final query for books
        final_query = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}}   # search by book title
            ]
        }
        if author_ids:
            final_query["$or"].append({"author_id": {"$in": author_ids}})

        found_books = list(books.find(final_query).sort("title", 1))

        html += f"<p>Знайдено результатів: <b>{len(found_books)}</b></p>"

        if found_books:
            all_authors = {a["_id"]: f"{a['name']} {a['surname']}" for a in authors.find()}

            html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
            html += "<tr><th>ID</th><th>Назва</th><th>Рік</th><th>Автор</th><th>Статус</th><th>Дії</th></tr>"
            
            for book in found_books:
                author_name = all_authors.get(book.get("author_id"), "Невідомий автор")
                status = "Доступна" if book.get("available", True) else "Видана"
                
                actions = ""
                if role == "admin":
                    actions += f"<a href='/books/{book['_id']}/edit?role=admin'>Редагувати</a> | "
                    actions += f"<a href='/books/{book['_id']}/delete?role=admin' onclick=\"return confirm('Видалити?')\">Видалити</a>"
                else:
                    if book.get("available", True):
                        actions += f"<a href='/books/{book['_id']}/borrow?role=user'>Позичити</a>"
                
                html += f"""
                <tr>
                    <td>{book['_id']}</td>
                    <td>{book['title']}</td>
                    <td>{book.get('year', '')}</td>
                    <td>{author_name}</td>
                    <td>{status}</td>
                    <td>{actions}</td>
                </tr>"""
            html += "</table>"
        else:
            html += "<p>Нічого не знайдено за вашим запитом.</p>"
    else:
        html += "<p>Введіть назву книги або ім’я/прізвище автора.</p>"

    html += f"<br><a href='/?role={role}'>← На головну</a>"
    return HTMLResponse(content=html)

# ====================== LIST BOOKS (with real author names) ======================
@app.get("/books", response_class=HTMLResponse)
async def list_books(role: str = "user"):
    all_books = list(books.find().sort("title", 1))
    
    # Pre-load all authors for fast lookup
    all_authors = {a["_id"]: f"{a['name']} {a['surname']}" for a in authors.find()}
    
    html = f"<h1>Список книг (Режим: {role.upper()}) - MongoDB</h1>"
    html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th>ID</th><th>Назва</th><th>Рік</th><th>Автор</th><th>Статус</th><th>Дії</th></tr>"
    
    for book in all_books:
        author_name = all_authors.get(book.get("author_id"), "Невідомий автор")
        status = "Доступна" if book.get("available", True) else "Видана"
        
        actions = ""
        if role == "admin":
            actions += f"<a href='/books/{book['_id']}/edit?role=admin'>Редагувати</a> | "
            actions += f"<a href='/books/{book['_id']}/delete?role=admin' onclick=\"return confirm('Видалити?')\">Видалити</a>"
            if not book.get("available", True):
                actions += f" | <a href='/books/{book['_id']}/return?role=admin' onclick=\"return confirm('Повернути?')\">Повернути</a>"
        else:
            if book.get("available", True):
                actions += f"<a href='/books/{book['_id']}/borrow?role=user'>Позичити</a>"
        
        html += f"""
        <tr>
            <td>{book['_id']}</td>
            <td>{book['title']}</td>
            <td>{book.get('year', '')}</td>
            <td>{author_name}</td>
            <td>{status}</td>
            <td>{actions}</td>
        </tr>"""
    
    html += "</table><br>"
    if role == "admin":
        html += "<a href='/books/add?role=admin'>Додати нову книгу</a> | "
    html += f"<a href='/?role={role}'>← На головну</a>"
    return HTMLResponse(content=html)

# ====================== CREATE (with author dropdown) ======================
@app.get("/books/add", response_class=HTMLResponse)
async def add_book_form(role: str = "user"):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    
    # Get all authors for dropdown
    all_authors = list(authors.find().sort("surname", 1))
    
    options = ""
    for a in all_authors:
        options += f'<option value="{a["_id"]}">{a["_id"]} - {a["name"]} {a["surname"]}</option>'
    
    html = f"""
    <h1>Додати нову книгу</h1>
    <form action="/books" method="post">
        <p>Назва: <input type="text" name="title" required></p>
        <p>Рік видання: <input type="number" name="year" required></p>
        <p>Автор: 
            <select name="author_id" required>
                {options}
            </select>
        </p>
        <button type="submit">Додати книгу</button>
    </form>
    <br><a href="/books?role=admin">← Назад</a>
    """
    return HTMLResponse(content=html)

@app.post("/books")
async def create_book(title: str = Form(...), year: int = Form(...), author_id: int = Form(...), role: str = "user"):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    
    new_book = {
        "title": title,
        "year": year,
        "author_id": author_id,
        "available": True
    }
    books.insert_one(new_book)
    return RedirectResponse(url="/books?role=admin", status_code=303)

# ====================== UPDATE (EDIT FORM) ======================
@app.get("/books/{book_id}/edit", response_class=HTMLResponse)
async def edit_book_form(book_id: int, role: str = "user"):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    
    book = books.find_one({"_id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Книга не знайдена")
    
    # Get all authors for dropdown
    all_authors = list(authors.find().sort("surname", 1))
    
    options = ""
    for a in all_authors:
        selected = "selected" if a["_id"] == book.get("author_id") else ""
        options += f'<option value="{a["_id"]}" {selected}>{a["_id"]} - {a["name"]} {a["surname"]}</option>'
    
    html = f"""
    <h1>Редагувати книгу</h1>
    <form action="/books/{book_id}/update" method="post">
        <p>Назва: <input type="text" name="title" value="{book['title']}" required></p>
        <p>Рік видання: <input type="number" name="year" value="{book.get('year', '')}" required></p>
        <p>Автор: 
            <select name="author_id" required>
                {options}
            </select>
        </p>
        <button type="submit">Зберегти зміни</button>
    </form>
    <br><a href="/books?role=admin">← Назад до списку</a>
    """
    return HTMLResponse(content=html)

@app.post("/books/{book_id}/update")
async def update_book(book_id: int, title: str = Form(...), year: int = Form(...), 
                      author_id: int = Form(...), role: str = "user"):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    
    books.update_one(
        {"_id": book_id}, 
        {"$set": {"title": title, "year": year, "author_id": author_id}}
    )
    return RedirectResponse(url="/books?role=admin", status_code=303)

@app.get("/books/{book_id}/delete")
async def delete_book(book_id: int, role: str = "user"):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    books.delete_one({"_id": book_id})
    return RedirectResponse(url="/books?role=admin", status_code=303)

# ====================== BORROW & RETURN ======================
@app.get("/books/{book_id}/borrow")
async def borrow_book(book_id: int, role: str = "user"):
    if role != "user":
        return RedirectResponse(url="/books?role=user")
    book = books.find_one({"_id": book_id})
    if not book or not book.get("available", True):
        raise HTTPException(status_code=400, detail="Книга недоступна")
    
    books.update_one({"_id": book_id}, {"$set": {"available": False}})
    loans.insert_one({
        "book_id": book_id,
        "user_name": "Тестовий Користувач",
        "loan_date": datetime.now(),
        "return_date": None
    })
    return RedirectResponse(url="/books?role=user", status_code=303)

@app.get("/books/{book_id}/return")
async def return_book(book_id: int, role: str = "user"):
    if role != "admin":
        return RedirectResponse(url="/books?role=user")
    books.update_one({"_id": book_id}, {"$set": {"available": True}})
    loans.update_one({"book_id": book_id, "return_date": None}, {"$set": {"return_date": datetime.now()}})
    return RedirectResponse(url="/books?role=admin", status_code=303)

# ====================== NEW FUNCTIONALITY (pymongo) ======================
@app.get("/stats", response_class=HTMLResponse)
async def mongo_stats():
    # Example of aggregation using pymongo
    pipeline = [
        {"$group": {
            "_id": "$author_id",
            "book_count": {"$sum": 1},
            "available_count": {"$sum": {"$cond": ["$available", 1, 0]}}
        }},
        {"$sort": {"book_count": -1}}
    ]
    stats = list(books.aggregate(pipeline))
    
    html = "<h1>Статистика бібліотеки</h1>"
    html += f"<p><b>Всього книг:</b> {books.count_documents({})}</p>"
    html += f"<p><b>Доступних книг:</b> {books.count_documents({'available': True})}</p>"
    html += "<h2>Кількість книг по авторах</h2>"
    html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    html += "<tr><th>Автор ID</th><th>Всього книг</th><th>Доступно</th></tr>"
    for s in stats:
        html += f"<tr><td>{s['_id']}</td><td>{s['book_count']}</td><td>{s['available_count']}</td></tr>"
    html += "</table><br><a href='/'>← На головну</a>"
    return HTMLResponse(content=html)