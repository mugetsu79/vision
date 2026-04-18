import sqlite3
import logging
import config

def init_db():
    try:
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            # Create traffic_data table with improved schema
            c.execute('''
                CREATE TABLE IF NOT EXISTS traffic_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    car_count INTEGER NOT NULL,
                    interval_start DATETIME
                )
            ''')
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"An error occurred: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR, filename='traffic_monitor.log',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    init_db()

