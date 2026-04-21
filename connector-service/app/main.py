from fastapi import FastAPI

app = FastAPI(title="Connector Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
