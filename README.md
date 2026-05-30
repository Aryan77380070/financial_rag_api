Here is a complete, professional `README.md` file designed specifically for your GitHub repository. It covers the architecture, setup instructions, and explains the crucial pieces of code that make your AI-powered backend work.

You can copy and paste everything below this line directly into your `README.md` file.

---

# Financial Document Management API with Semantic Search 📊🧠

A robust, enterprise-ready REST API built with **FastAPI** that allows organizations to securely store, manage, and analyze financial documents.

This project goes beyond standard file storage by implementing a complete **Retrieval-Augmented Generation (RAG)** pipeline. It uses local vector databases and open-source AI models (Bi-encoders and Cross-encoders) to perform highly accurate semantic searches across uploaded PDF documents (invoices, reports, contracts).

## 🚀 Tech Stack

* **Backend Framework:** FastAPI, Uvicorn
* **Database:** PostgreSQL, SQLAlchemy (ORM)
* **Authentication:** JWT (JSON Web Tokens), `passlib`, `bcrypt`
* **AI & NLP:** LangChain, HuggingFace (`all-MiniLM-L6-v2`), Sentence-Transformers (`ms-marco-MiniLM-L-6-v2`)
* **Vector Database:** ChromaDB (Local)
* **Document Processing:** PyPDF

---

## ✨ Core Features

1. **Role-Based Access Control (RBAC):** Secure endpoints restricted by user roles (Admin, Financial Analyst, Auditor, Client).
2. **Relational Metadata Storage:** Tracks document details (company name, uploader, timestamps) in PostgreSQL.
3. **AI Document Ingestion:** Automatically extracts text from uploaded PDFs, chunks it contextually, generates vector embeddings, and stores them in ChromaDB.
4. **Two-Stage Semantic Search:** Uses a fast vector search to find the top 20 results, followed by a highly accurate AI reranking model to return the top 5 most relevant insights.

---

## 🛠️ Local Setup & Installation

### 1. Prerequisites

* Python 3.10+
* PostgreSQL server running locally

### 2. Environment Setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/yourusername/financial-rag-api.git
cd financial-rag-api
python -m venv venv

# Activate on Windows:
venv\Scripts\activate
# Activate on macOS/Linux:
source venv/bin/activate

```

Install the dependencies:

```bash
pip install -r requirements.txt

```

*(Note: If you encounter an error with `passlib` hashing, ensure you are using `bcrypt==3.2.2`)*.

### 3. Environment Variables

Create a `.env` file in the root directory and configure your PostgreSQL connection and JWT secrets:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/financial_db
SECRET_KEY=your_super_secret_random_hex_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

```

### 4. Database Initialization

Ensure you have created an empty database named `financial_db` in PostgreSQL. The FastAPI application will automatically generate the required tables on the first run.

```bash
psql -U postgres
CREATE DATABASE financial_db;
\q

```

### 5. Run the Server

```bash
uvicorn app.main:app --reload

```

Navigate to `http://127.0.0.1:8000/docs` to view the interactive Swagger UI and test the endpoints.

---

## 📂 Architecture & Crucial Code Explanations

### 1. Security & RBAC (`app/auth.py`)

Security is handled via OAuth2 with Password Bearer tokens. We implemented a custom `RoleChecker` dependency to protect routes.

```python
# Crucial Code: Role-Based Access Control Dependency
class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)):
        # Checks if the authenticated user has a role permitted to access the endpoint
        if not current_user.role or current_user.role.name not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return current_user

# Usage in a route: Only Admins can delete documents
@router.delete("/{document_id}")
def delete_document(
    document_id: int, 
    current_user: models.User = Depends(RoleChecker(["Admin"])) 
):

```

### 2. File Uploads & Relational Syncing (`app/documents.py`)

When a document is uploaded, the physical PDF is saved to a local `uploads/` directory, while its metadata is stored in PostgreSQL. This ensures our AI pipeline always has a physical file to read from.

```python
# Crucial Code: Handling Multipart Form Data
@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_name: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Save physical file
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Save metadata to Postgres
    new_doc = models.Document(title=title, company_name=company_name)
    db.add(new_doc)
    db.commit()

```

### 3. AI Document Ingestion Pipeline (`app/rag_core.py`)

This is the heart of the RAG system. We extract text from PDFs, split it into overlapping chunks (so sentences aren't cut in half), embed them using HuggingFace, and save them to ChromaDB.

```python
# Crucial Code: Text Chunking and Embedding
def process_and_index_document(document_id: int, file_path: str, metadata: dict):
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # Split text into 1000-character chunks with a 150-character overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=150
    )
    chunks = text_splitter.split_documents(pages)

    # Attach relational database metadata to the AI chunks
    for chunk in chunks:
        chunk.metadata.update(metadata)
        chunk.metadata["document_id"] = document_id 

    # Save to local Vector Database
    vectorstore = Chroma(persist_directory="chroma_db", embedding_function=HuggingFaceEmbeddings())
    vectorstore.add_documents(chunks)

```

### 4. Advanced Two-Stage Retrieval (`app/rag_core.py`)

To provide the highest accuracy possible, the search endpoint uses a Bi-Encoder to fetch the top 20 results instantly, and then a heavy Cross-Encoder to read the context deeply and rank the top 5.

```python
# Crucial Code: Semantic Search & Reranking
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def retrieve_and_rerank(query: str):
    # Stage 1: Fast Vector Search (Top 20)
    initial_results = vectorstore.similarity_search(query, k=20)
    
    # Stage 2: Cross-Encoder Reranking
    # Prepare pairs of [User Query, Document Chunk]
    pairs = [[query, doc.page_content] for doc in initial_results]
    
    # AI generates a contextual relevance score for each pair
    scores = reranker.predict(pairs)
    
    # Sort documents by their AI score descending and return Top 5
    scored_results = list(zip(initial_results, scores))
    scored_results.sort(key=lambda x: x[1], reverse=True)
    
    return scored_results[:5]

```

---

## 🚀 Deployment Instructions

This application requires persistent storage for the `uploads/` and `chroma_db/` folders.

If deploying to a PaaS like Render or Railway:

1. Provision a managed PostgreSQL database.
2. Deploy the FastAPI code as a Web Service.
3. **Crucial:** Attach a Persistent Disk to your web service and map it to your storage directories to ensure files and AI embeddings survive server restarts.
4. Update the start command to use Gunicorn:
`gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
