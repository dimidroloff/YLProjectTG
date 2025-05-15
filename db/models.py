from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)     # публичный код
    password = Column(String, nullable=False)              # пароль
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="account", cascade="all, delete")
    expenses = relationship("Expense", back_populates="account", cascade="all, delete")


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)  # Telegram user_id
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"))

    account = relationship("Account", back_populates="users")
    expenses = relationship("Expense", back_populates="user", cascade="all, delete")


class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    category = Column(String, nullable=False)
    comment = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    account = relationship("Account", back_populates="expenses")
    user = relationship("User", back_populates="expenses")
