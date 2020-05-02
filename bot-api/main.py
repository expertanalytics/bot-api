from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "world"}

@app.post("/events")
async def events(request: Request):
    req = await request.body()
    print(req)

    return {"challenge": req["token"]}
