from sqlalchemy import inspect, text
from database.models import Base

def initialize_database(engine):
    """Create tables and add missing fields to older local installations."""
    Base.metadata.create_all(bind=engine)
    for table in Base.metadata.sorted_tables:
        existing = {column['name'] for column in inspect(engine).get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing:
                column_type = column.type.compile(dialect=engine.dialect)
                with engine.begin() as migration:
                    migration.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}'))
