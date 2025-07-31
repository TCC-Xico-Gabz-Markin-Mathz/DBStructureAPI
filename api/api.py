import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from api.dependencies import get_api_key
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Security
from api.logs.helpers.db_logs import analyse_logs
from api.structure.routes import db_structure
from api.optimization.routes import optimization

scheduler = BackgroundScheduler()
app = FastAPI(dependencies=[Security(get_api_key)])

scheduler.add_job(analyse_logs, CronTrigger(second=3))
scheduler.start()

@atexit.register
def shutdown():
    scheduler.shutdown()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(db_structure.router)
app.include_router(optimization.router)

@app.get("/")
def read_root():
    return {"message": "to see the documentation got to the route '/docs'."}
