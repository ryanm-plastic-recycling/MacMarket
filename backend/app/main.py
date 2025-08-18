from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal, Base, engine
from . import models, schemas, crud
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MacMarket Alert API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def root():
    html_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>MacMarket Alert API</h1>"

@app.get("/users/{user_id}/alerts", response_model=list[schemas.AlertPreference])
def read_alerts(user_id: int, db: Session = Depends(get_db)):
    return crud.get_alerts(db, user_id)

@app.post("/users/{user_id}/alerts", response_model=schemas.AlertPreference)
def create_alert(user_id: int, alert: schemas.AlertPreferenceCreate, db: Session = Depends(get_db)):
    if not crud.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return crud.create_alert(db, user_id, alert)

@app.put("/users/{user_id}/alerts/{alert_id}", response_model=schemas.AlertPreference)
def update_alert(user_id: int, alert_id: int, alert: schemas.AlertPreferenceUpdate, db: Session = Depends(get_db)):
    alert_obj = crud.get_alert(db, user_id, alert_id)
    if not alert_obj:
        raise HTTPException(status_code=404, detail="Alert not found")
    return crud.update_alert(db, alert_obj, alert)

@app.delete("/users/{user_id}/alerts/{alert_id}")
def delete_alert(user_id: int, alert_id: int, db: Session = Depends(get_db)):
    alert_obj = crud.get_alert(db, user_id, alert_id)
    if not alert_obj:
        raise HTTPException(status_code=404, detail="Alert not found")
    crud.delete_alert(db, alert_obj)
    return {"status": "deleted"}


@app.get("/users/{user_id}/haco-alerts", response_model=list[schemas.HacoAlert])
def read_haco_alerts(user_id: int, db: Session = Depends(get_db)):
    return crud.get_haco_alerts(db, user_id)


@app.post("/users/{user_id}/haco-alerts", response_model=schemas.HacoAlert)
def create_haco_alert(user_id: int, alert: schemas.HacoAlertCreate, db: Session = Depends(get_db)):
    if not crud.get_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return crud.create_haco_alert(db, user_id, alert)


@app.put("/users/{user_id}/haco-alerts/{alert_id}", response_model=schemas.HacoAlert)
def update_haco_alert(user_id: int, alert_id: int, alert: schemas.HacoAlertUpdate, db: Session = Depends(get_db)):
    alert_obj = crud.get_haco_alert(db, user_id, alert_id)
    if not alert_obj:
        raise HTTPException(status_code=404, detail="Alert not found")
    return crud.update_haco_alert(db, alert_obj, alert)


@app.delete("/users/{user_id}/haco-alerts/{alert_id}")
def delete_haco_alert(user_id: int, alert_id: int, db: Session = Depends(get_db)):
    alert_obj = crud.get_haco_alert(db, user_id, alert_id)
    if not alert_obj:
        raise HTTPException(status_code=404, detail="Alert not found")
    crud.delete_haco_alert(db, alert_obj)
    return {"status": "deleted"}
