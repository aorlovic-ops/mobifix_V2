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

class Servis(Base):
    __tablename__ = "servisi"
    
    id = Column(Integer, primary_key=True, index=True)
    naziv_obrta = Column(String, nullable=False)
    vlasnik_ime = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    lozinka_hash = Column(String, nullable=False)
    datum_registracije = Column(DateTime, default=datetime.now)
    
    klijenti = relationship("Klijent", back_populates="servis")
    nalozi = relationship("ServisniNalog", back_populates="servis")

class Klijent(Base):
    __tablename__ = "klijenti"
    
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    ime_prezime = Column(String, nullable=False)
    broj_telefona = Column(String, nullable=False)
    email = Column(String, nullable=False)
    datum_kreiranja = Column(DateTime, default=datetime.now)
    
    servis = relationship("Servis", back_populates="klijenti")
    nalozi = relationship("ServisniNalog", back_populates="klijent")

class ServisniNalog(Base):
    __tablename__ = "servisni_nalozi"
    
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    klijent_id = Column(Integer, ForeignKey("klijenti.id"), nullable=False)
    tracking_token = Column(String, default=lambda: secrets.token_hex(4), nullable=False)
    brand = Column(String, nullable=False)
    model_uredjaja = Column(String, nullable=False)
    serijski_imei = Column(String, nullable=False)
    opis_kvara = Column(Text, nullable=False)
    status = Column(String, default='Zaprimljeno', nullable=False)
    datum_zaprimanja = Column(DateTime, default=datetime.now)
    datum_preuzimanja = Column(DateTime, nullable=True)
    dogovorena_cijena = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    
    servis = relationship("Servis", back_populates="nalozi")
    klijent = relationship("Klijent", back_populates="nalozi")

    @property
    def profesionalni_id(self):
        return f"MFIX-{self.datum_zaprimanja.strftime('%y')}-{self.id:04d}"

# Automatsko kreiranje tablica pri pokretanju
Base.metadata.create_all(bind=engine)