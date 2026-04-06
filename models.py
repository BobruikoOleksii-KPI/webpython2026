from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import date


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    surname = Column(String, index=True, nullable=False)
    birth_year = Column(Integer)

    books = relationship("Book", back_populates="author")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    year = Column(Integer)
    author_id = Column(Integer, ForeignKey("authors.id"))
    available = Column(Boolean, default=True)

    author = relationship("Author", back_populates="books")
    loans = relationship("Loan", back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_name = Column(String, nullable=False)
    loan_date = Column(Date, default=date.today)
    return_date = Column(Date, nullable=True)

    book = relationship("Book", back_populates="loans")