import logging
from datetime import datetime

import discord
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import Reminder, Session

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
        return reminders if reminders else []
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while retrieving pending reminders: {e}", exc_info=True)
    finally:
        session.close()
    return []

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

class AnalisisButton(discord.ui.Button):
    def __init__(self, message_id, channel_id):
        super().__init__(label="Análisis", style=discord.ButtonStyle.grey)
        self.message_id = message_id
        self.target_channel_id = channel_id


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            thread_id = self.message_id # The message_id is == thread_id

            if thread_id:
                original_thread = interaction.client.get_channel(int(thread_id))
                target_channel = interaction.client.get_channel(self.target_channel_id)

                if original_thread:
                    
                    new_thread = await target_channel.create_thread(
                            name= f"Análisis de Mensaje {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            message=interaction.message
                        )

                    await copy_messages_to_new_thread(interaction.client, thread_id, new_thread)

                    await interaction.followup.send(
                        f"Los mensajes del hilo {original_thread.name} se han copiado al hilo {new_thread.name} en el canal {target_channel.name}",
                        ephemeral=True
                        )

                else:
                    await interaction.followup.send("El hilo original no está disponible.", ephemeral=True)
            else:
                await interaction.followup.send(f"No hay un hilo específico asociado para análisis. {self.message_id} ", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.followup.send("El mensaje original no se pudo encontrar.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ocurrió un error: {e}", ephemeral=True)


async def copy_messages_to_new_thread(bot, original_thread_id, new_thread: discord.Thread):
    try:
        original_thread = bot.get_channel(original_thread_id)
        if original_thread:
            # Verifica si original_thread es realmente un Thread y no un Channel regular
            if isinstance(original_thread, discord.Thread):

                async for message in original_thread.history(limit=123, oldest_first=True):
                    if message.content:
                        await new_thread.send(message.content)

            else:
                logger.error(f"El ID {original_thread_id} no corresponde a un hilo válido.")
        else:
            logger.error(f"No se encontró el hilo con ID {original_thread_id}.")
    except Exception as e:
        logger.error(f"Ocurrió un error al copiar mensajes al nuevo hilo: {e}", exc_info=True)