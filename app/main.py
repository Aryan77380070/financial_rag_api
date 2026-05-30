from fastapi import FastAPI
from .database import engine, Base
from . import models, auth, documents, rag_api # <-- Import rag_api

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Financial Document Management API")

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(rag_api.router) # <-- Add this line

@app.get("/")
def read_root():
    return {"message": "Welcome to the Financial Document Management API"}