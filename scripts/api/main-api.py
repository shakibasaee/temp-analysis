from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
def read_root():
    return {"massage": "ML API is running"}

class PredictionInput(BaseModel):
    lag1: float
    lag2: float
    lag3: float
    