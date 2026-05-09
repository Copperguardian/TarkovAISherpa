import sqlite3
import os

db_path = r'c:\Users\User\Desktop\COSAS_INTELIGENCIA_ARTIFICAL\Programacion_Inteligencia_Artificial\Agentes\Langchain\Proyecto\TarkovAISherpa\Backend\tarkov_sherpa.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'thread_id' not in columns:
        print("Adding thread_id column to conversations table...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN thread_id TEXT")
        conn.commit()
        print("Column added successfully.")
    else:
        print("thread_id column already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")

