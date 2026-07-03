from pipeline.kafka_worker import TrainingWorker
from database.connection import SessionLocal

# Shared training worker instance connected to the DB sessions factory
worker = TrainingWorker(db_session_maker=SessionLocal)
worker.start()
