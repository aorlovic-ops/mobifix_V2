from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, create_engine, sessionmaker

# Kreiranje lokalne SQLite baze podataka
DATABASE_URL = "sqlite:///./mobifix.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Servis(Base):
    __tablename__ = "servisi"
    id = Column(Integer, primary_key=True, index=True)
    naziv_obrta = Column(String, nullable=False)
    vlasnik_ime = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    lozinka_hash = Column(String, nullable=False)
    nalozi = relationship("ServisniNalog", back_populates="servis")

class Klijent(Base):
    __tablename__ = "klijenti"
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    ime_prezime = Column(String, nullable=False)
    broj_telefona = Column(String, nullable=False)
    email = Column(String, nullable=False)
    nalozi = relationship("ServisniNalog", back_populates="klijent")

class ServisniNalog(Base):
    __tablename__ = "servisni_nalozi"
    id = Column(Integer, primary_key=True, index=True)
    servis_id = Column(Integer, ForeignKey("servisi.id"), nullable=False)
    klijent_id = Column(Integer, ForeignKey("klijenti.id"), nullable=False)
    tracking_token = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    model_uredjaja = Column(String, nullable=False)
    imei_sn = Column(String, default="")
    opis_kvara = Column(Text, nullable=False)
    status = Column(String, default='zaprimljeno')
    napomena_servisera = Column(Text, default="")
    
    # Polja za oštećenja (model podataka)
    ostecen_ekran = Column(Integer, default=0)
    ostecenje_vlagom = Column(Integer, default=0)
    
    servis = relationship("Servis", back_populates="nalozi")
    klijent = relationship("Klijent", back_populates="nalozi")