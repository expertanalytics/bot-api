from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "world"}

@app.get("/events")
async def events():
    return 
