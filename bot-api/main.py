from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "world"}

@app.get("/events")
async def events(request: Request):
    print(request)
    return 
