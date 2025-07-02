from sqlalchemy.orm import Session
from . import models, schemas

# User helper functions

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

# AlertPreference CRUD

def get_alert(db: Session, user_id: int, alert_id: int):
    return (
        db.query(models.AlertPreference)
        .filter(models.AlertPreference.user_id == user_id, models.AlertPreference.id == alert_id)
        .first()
    )

def get_alerts(db: Session, user_id: int):
    return db.query(models.AlertPreference).filter(models.AlertPreference.user_id == user_id).all()

def create_alert(db: Session, user_id: int, alert: schemas.AlertPreferenceCreate):
    db_alert = models.AlertPreference(user_id=user_id, **alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def update_alert(db: Session, alert_obj: models.AlertPreference, alert: schemas.AlertPreferenceUpdate):
    for field, value in alert.dict(exclude_unset=True).items():
        setattr(alert_obj, field, value)
    db.add(alert_obj)
    db.commit()
    db.refresh(alert_obj)
    return alert_obj

def delete_alert(db: Session, alert_obj: models.AlertPreference):
    db.delete(alert_obj)
    db.commit()
