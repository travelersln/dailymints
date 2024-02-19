# reminder_tasks.py
import discord
from discord.ext import tasks
from discord.ui import Button, View
from datetime import datetime, timedelta
import re
from datetime import datetime, timedelta
from database_operations import add_reminder, get_pending_reminders, update_reminder_status, delete_past_reminders, check_reminder_exists, delete_notified_reminders
import logging

# Configura el logging
logger = logging.getLogger('reminder_tasks')



active_views = {}

def extract_event_time(event_text):
    match = re.search(r'<t:(\d+):F>', event_text)
    if match:
        event_unix_time = int(match.group(1))
        return datetime.utcfromtimestamp(event_unix_time)
    return None

class ReminderButton(Button):
    def __init__(self, label, custom_id, event_text, disabled=False):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji="🔔", custom_id=custom_id)
        self.event_text = event_text
        self.event_time = extract_event_time(event_text)
        self.disabled = disabled

    async def callback(self, interaction):
        try:
            current_time = datetime.utcnow()
            # Desactivar el botón si falta menos de 40 minutos para el evento
            if self.disabled or (current_time + timedelta(minutes=40)) >= self.event_time:
                await interaction.response.send_message(
                    "This event can no longer be reminded as it's too close to the start time.",
                    ephemeral=True
                )
                return  # Terminar la ejecución si el evento está muy cerca

            # Comprobar si ya existe un recordatorio para este usuario y evento
            exists = check_reminder_exists(interaction.user.id, self.custom_id)
            if exists:
                await interaction.response.send_message(
                    "You have already set a reminder for this event.",
                    ephemeral=True
                )
                return  # Terminar la ejecución si el recordatorio ya existe

            # Agregar un nuevo recordatorio si no existe
            guild_id = interaction.guild.id
            channel_id = interaction.channel.id
            message_id = interaction.message.id
            add_reminder(interaction.user.id, self.custom_id, self.event_time, guild_id, channel_id, message_id)

            # Notificar al usuario que el recordatorio se ha configurado
            reminder_time = self.event_time - timedelta(minutes=30)
            await interaction.response.send_message(
                f"Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M:%S')} UTC.",
                ephemeral=True
            )

        except Exception as e:
            # Registrar el error y enviar un mensaje al usuario
            logger.error(f"Error in callback: {e}", exc_info=True)
            await interaction.response.send_message(
                "An error occurred while processing your reminder.",
                ephemeral=True

            )


def generate_reminder_button(event_text: str, mint_num: int = 1) -> ReminderButton:
    # Get the current time in UTC
    current_time = datetime.utcnow()

    # Extract the event time from the event text (assuming it's a function defined elsewhere)
    event_time = extract_event_time(event_text)

    # Calculate whether the button should be disabled based on event time
    disabled = (current_time + timedelta(minutes=40)) >= event_time

    # Create and return a ReminderButton instance with appropriate parameters
    return ReminderButton(f"Mint {mint_num}", f"reminder_{mint_num}", event_text, disabled=disabled)

class MessageSentView(View):
    def __init__(self, buttons):
        # Call the constructor of the parent class (View) with timeout set to None
        super().__init__(timeout=None)

        # Add each button provided to the view
        for button in buttons:
            self.add_item(button)

class ReminderView(View):
    def __init__(self, event_texts):
        super().__init__(timeout=None)
        for i, event_text in enumerate(event_texts):
            self.add_item(generate_reminder_button(event_text, i+1))


async def send_reminder_view(bot, channel_id, event_texts):
    channel = bot.get_channel(channel_id)
    if channel:
        view = ReminderView(event_texts)
        message = await channel.send("Here are your reminders:", view=view)
        # Actualizar active_views con el ID del mensaje y la vista asociada
        active_views[message.id] = view

@tasks.loop(seconds=60)
async def reminder_check(bot):
    logger.info("Checking reminders...")
    try:
        reminders = get_pending_reminders()
        current_time = datetime.utcnow()
        logger.debug(f"Current time: {current_time}")
        for reminder in reminders:
            time_difference = (reminder.event_time - current_time).total_seconds()
            logger.debug(f"Checking reminder for user {reminder.user_id}: event time {reminder.event_time}, time difference {time_difference}")
            if 0 < time_difference <= 1800 and reminder.status == 'pending':
                logger.info(f"Preparing to send a reminder for user {reminder.user_id}")
                try:
                    user = await bot.fetch_user(reminder.user_id)
                    message_link = f"https://discord.com/channels/{reminder.guild_id}/{reminder.channel_id}/{reminder.message_id}"
                    message_content = f"¡Remember the mint {reminder.custom_id} from your reminder at {message_link}!"
                    message = await user.send(message_content)
                    if message:
                        logger.info(f"Se envió el recordatorio al usuario {reminder.user_id}. Actualizando el estado ahora.")
                        update_reminder_status(reminder.id, 'notified')
                        logger.info(f"Updated reminder status to 'notified' for user {reminder.user_id}")
                        delete_notified_reminders()
                        logger.info(f"Estado del recordatorio actualizado a 'notified' y se intentó eliminar los recordatorios notificados para el usuario {reminder.user_id}")
                except Exception as e:
                    logger.error(f"Se produjo un error en la comprobación del recordatorio: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An error occurred in reminder_check: {e}", exc_info=True)
@tasks.loop(minutes=1)
async def cleanup_past_reminders():
    logger.info("Limpiando recordatorios pasados...")
    try:
        # Obtén la hora actual
        current_time = datetime.utcnow()
        # Ahora se llamará a la función para borrar recordatorios notificados
        delete_past_reminders(current_time, 'notified')
        logger.info("Los recordatorios pasados han sido limpiados.")
    except Exception as e:
        logger.error(f"Ocurrió un error en cleanup_past_reminders: {e}", exc_info=True)

@tasks.loop(minutes=1)
async def update_button_states(bot):
    current_time = datetime.utcnow()
    for message_id, view in list(active_views.items()):
        should_update = False
        for item in view.children:
            if isinstance(item, ReminderButton):
                if (current_time + timedelta(minutes=40)) >= item.event_time and not item.disabled:
                    item.disabled = True
                    should_update = True
        if should_update:
            channel = bot.get_channel(view.channel_id)
            message = await channel.fetch_message(message_id)
            await message.edit(view=view)

def setup_tasks(bot):
    reminder_check.start(bot)
    cleanup_past_reminders.start()
    update_button_states.start(bot)
