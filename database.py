from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session


Base = declarative_base()


class HomeWork(Base):
    """Создание таблицы для записи данных полученных от API."""
    __tablename__ = 'homeworks'
    id = Column('id', Integer, primary_key=True)
    name = Column('name', String)
    status = Column('status', String)
    current_date = Column('current_date', Integer)

    def __init__(self, name, status, current_date):
        self.name = name
        self.status = status
        self.current_date = current_date

    def __repr__(self):
        return f'{self.id} - {self.name} - {self.status} {self.current_date}'


class ErrorLog(Base):
    """Создание таблицы для записи ошибок."""
    __tablename__ = 'errors'
    id = Column('id', Integer, primary_key=True)
    message = Column('message', String)
    created_on = Column(DateTime(), default=datetime.now)

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return f'{self.id} - {self.message} - {self.created_on}'


engine = create_engine('sqlite:///tgdb.db', echo=True, echo_pool=True)
Base.metadata.create_all(bind=engine)


def db_insert_hw(name, status, current_date):
    """Функция для записи данных полученных от API в базу."""
    with Session(autoflush=False, bind=engine) as session:
        hw = HomeWork(name=name, status=status, current_date=current_date)
        session.add(hw)
        session.commit()


def db_insert_error(message):
    """Функция для записи данных ошибок в базу."""
    with Session(autoflush=False, bind=engine) as session:
        error_msg = ErrorLog(message=message)
        session.add(error_msg)
        session.commit()


def db_select_hw():
    """Получение из базы данных последней записи о домашней работе."""
    with Session(autoflush=False, bind=engine) as session:
        return session.query(HomeWork).order_by(HomeWork.id.desc()).first()


def db_select_error():
    """Получение из базы данных последней записи об ошибке."""
    with Session(autoflush=False, bind=engine) as session:
        return session.query(ErrorLog).order_by(ErrorLog.id.desc()).first()
