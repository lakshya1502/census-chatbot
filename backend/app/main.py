from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Census Chatbot API")

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Backend running"}