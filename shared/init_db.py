#!/usr/bin/env python3
"""
Database initialization script for the podcast research system.
Run this to create the SQLite database and all tables.
"""

from .database import db_manager
from .models import Base
import os

def init_database():
    """Initialize the database and create all tables"""
    print("Initializing podcast research database...")
    
    # Create the database directory if it doesn't exist
    db_path = "podcast_research.db"
    if os.path.exists(db_path):
        print(f"Database {db_path} already exists.")
        response = input("Do you want to recreate it? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing database.")
            return
        else:
            os.remove(db_path)
            print(f"Removed existing database {db_path}")
    
    # Create all tables
    db_manager.create_tables()
    print("✅ Database tables created successfully!")
    
    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(db_manager.engine)
    tables = inspector.get_table_names()
    
    print(f"Created tables: {', '.join(tables)}")
    
    # Create embeddings storage directory
    embeddings_dir = "embeddings_storage"
    if not os.path.exists(embeddings_dir):
        os.makedirs(embeddings_dir)
        print(f"✅ Created embeddings storage directory: {embeddings_dir}")
    
    print("\n🎉 Database initialization complete!")
    print("You can now run the podcast research agents.")

if __name__ == "__main__":
    init_database()