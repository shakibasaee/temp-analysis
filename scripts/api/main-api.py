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


@app.post("/predict")
def predict_temprature(data: PredictionInput):
    predicted_value = (data.lag1 + data.lag2 + data.lag3) / 3

    return {"predection_temprature": predicted_value}