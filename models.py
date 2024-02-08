import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv() 
Base = declarative_base()

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT')  # Asegúrate de haber añadido esta nueva variable de entorno.
MYSQL_DB = os.getenv('MYSQL_DB')

DATABASE_URL = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?ssl_ca=C:\\Users\\alato\\Downloads\\ca.pem"


engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255))
    custom_id = Column(String(255))
    event_time = Column(DateTime)
    status = Column(String(50))
    guild_id = Column(BigInteger)     
    channel_id = Column(BigInteger)  
    message_id = Column(BigInteger) 

    def __repr__(self):
        return f"<Reminder(user_id='{self.user_id}', custom_id='{self.custom_id}', event_time='{self.event_time}', status='{self.status}', guild_id='{self.guild_id}', channel_id='{self.channel_id}', message_id='{self.message_id}')>"

def init_db():
    Base.metadata.create_all(engine)
