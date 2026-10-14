from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Context Manager
class ContextManager:
    def __init__(self):
        self.context = []

    def add_context(self, item: dict):
        self.context.append(item)

    def get_context(self):
        return self.context

    def clear_context(self):
        self.context = []

context_manager = ContextManager()

# Models
class ContextItem(BaseModel):
    type: str # "text", "image"
    content: str
    metadata: Optional[dict] = {}

class PromptRequest(BaseModel):
    prompt_key: str
    input_data: str

# Routes
@app.get("/")
async def root():
    return {"message": "Study Partner Backend is running"}

@app.get("/context")
async def get_context():
    return context_manager.get_context()

@app.post("/context")
async def add_context(item: ContextItem):
    context_manager.add_context(item.dict())
    return {"message": "Context added"}

@app.delete("/context")
async def clear_context():
    context_manager.clear_context()
    return {"message": "Context cleared"}

# Load Prompts
PROMPTS_FILE = "src/backend/prompts.json"
prompts = {}

def load_prompts():
    global prompts
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, "r") as f:
            prompts = json.load(f)
    else:
        print(f"Warning: {PROMPTS_FILE} not found.")

@app.on_event("startup")
async def startup_event():
    load_prompts()

@app.get("/prompts")
async def get_prompts():
    return prompts
