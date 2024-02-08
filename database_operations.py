import logging
from models import Session, Reminder
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

logger = logging.getLogger('database_operations')

def add_reminder(user_id, custom_id, event_time, guild_id, channel_id, message_id):
    session = Session()
    try:
        new_reminder = Reminder(
            user_id=user_id,
            custom_id=custom_id,
            event_time=event_time,
            status='pending',
            guild_id=guild_id,      
            channel_id=channel_id,  
            message_id=message_id 
        )
        session.add(new_reminder)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"SQLAlchemyError occurred while adding a reminder: {e}", exc_info=True)
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error occurred while adding a reminder: {e}", exc_info=True)
    finally:
        session.close()

def check_reminder_exists(user_id, custom_id):
    session = Session()
    try:
        existing_reminder = session.query(Reminder).filter_by(
            user_id=user_id,
            custom_id=custom_id
        ).first()
        return existing_reminder is not None
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while checking if a reminder exists: {e}", exc_info=True)
        return False
    finally:
        session.close()
def get_pending_reminders():
    session = Session()
    try:
        current_time = datetime.utcnow()
        reminders = session.query(Reminder).filter(
            Reminder.event_time > current_time,
            Reminder.status == 'pending'
        ).all()
        return reminders
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while retrieving pending reminders: {e}", exc_info=True)
    finally:
        session.close()

def update_reminder_status(reminder_id, new_status):
    session = Session()
    try:
        reminder = session.query(Reminder).get(reminder_id)
        if reminder:
            reminder.status = new_status
            session.commit()
            logger.info(f"Reminder {reminder_id} status updated to {new_status}")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"SQLAlchemyError occurred while updating a reminder: {e}", exc_info=True)
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error occurred while updating a reminder: {e}", exc_info=True)
    finally:
        session.close()

def delete_past_reminders(current_time, status):
    session = Session()
    try:
        past_reminders = session.query(Reminder).filter(
            Reminder.event_time < current_time,
            Reminder.status == 'notified'
        ).all()
        for reminder in past_reminders:
            session.delete(reminder)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"An error occurred while deleting past reminders: {e}", exc_info=True)
    finally:
        session.close()
def delete_notified_reminders():
    session = Session()
    try:
        # Busca todos los recordatorios con estado 'notified'
        notified_reminders = session.query(Reminder).filter(
            Reminder.status == 'notified'
        ).all()
        for reminder in notified_reminders:
            # Elimina los recordatorios encontrados
            session.delete(reminder)
        session.commit()
        logger.info("Recordatorios notificados eliminados con éxito.")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Se produjo un error al eliminar recordatorios notificados: {e}", exc_info=True)
    finally:
        session.close()
        