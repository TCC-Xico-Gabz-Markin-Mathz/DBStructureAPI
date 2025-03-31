import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("api.api:app", host="0.0.0.0", port=8002, reload=True)
