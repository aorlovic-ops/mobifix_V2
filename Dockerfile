# 1. Koristimo službenu Python sliku
FROM python:3.11-slim

# 2. Postavljamo radni direktorij unutar kontejnera
WORKDIR /app

# 3. Kopiramo datoteku s paketima i instaliramo ih
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kopiramo ostatak koda aplikacije u kontejner
COPY . .

# 5. Otvaramo port 8000 na kojem će FastAPI raditi
EXPOSE 8000

# 6. Naredba za pokretanje Uvicorn servera
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]