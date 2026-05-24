from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import secrets
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'mobifix_saas.db')

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DODANI USER MODEL (korištenje istog sustava kao i ostali) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

# --- OSTALI TVOJI MODELI ---
class Servis(Base):
    __tablename__ = "servisi"
    id = Column(Integer, primary_key=True, index=True)
    naziv_obrta = Column(String, nullable=False)
    vlasnik_ime = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    lozinka_hash = Column(String, nullable=False)
    klijenti = relationship("Klijent", back_populates="servis")
    nalozi = relationship("ServisniNalog", back_populates="servis")

class Klijent(Base):
    __tablename__ = "klijenti"
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    ime_prezime = Column(String, nullable=False)
    broj_telefona = Column(String, nullable=False) # DODAJ OVO!
    email = Column(String, nullable=False)
    servis = relationship("Servis", back_populates="klijenti")
    nalozi = relationship("ServisniNalog", back_populates="klijent")

class ServisniNalog(Base):
    __tablename__ = "servisni_nalozi"
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    klijent_id = Column(Integer, ForeignKey("klijenti.id"), nullable=False)
    status = Column(String, default='zaprimljeno')
    servis = relationship("Servis", back_populates="nalozi")
    klijent = relationship("Klijent", back_populates="nalozi")
class Servis(Base):
    __tablename__ = "servisi"
    id = Column(Integer, primary_key=True)
    naziv_obrta = Column(String)
    vlasnik_ime = Column(String)
    email = Column(String, unique=True)
    lozinka_hash = Column(String)