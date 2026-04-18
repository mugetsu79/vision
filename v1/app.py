import eventlet
eventlet.monkey_patch()

import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from car_detection import CarDetector
import base64
import threading
import logging
import config
import traceback
from collections import deque
from dateutil import parser

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# Setup logging
logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)

def init_db():
    try:
        with sqlite3.connect(config.DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS traffic_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    car_count INTEGER NOT NULL,
                    interval_start DATETIME
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"An error occurred initializing database: {e}")

class TrafficMonitor:
    def __init__(self):
        self.camera = None
        self.detector = CarDetector()
        self.total_car_count = 0
        self.tracking_active = False
        self.frame_queue = deque(maxlen=10)
        self.lock = threading.Lock()
        self.capture_thread = None
        self.process_thread = None

    def init_camera(self):
        try:
            # Standard VideoCapture initialization without special options
            self.camera = cv2.VideoCapture(config.RTSP_URL)
            if not self.camera.isOpened():
                logger.error("Error: Could not open video stream from RTSP camera.")
            else:
                logger.info("Successfully connected to the RTSP camera.")
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 10)
        except Exception as e:
            logger.error(f"Exception in init_camera: {e}")
            self.camera = None

    def reconnect_camera(self):
        if self.camera:
            self.camera.release()
        time.sleep(2)  # Short delay before reconnect
        logger.info("Attempting to reconnect to the camera...")
        self.init_camera()

    def capture_frames(self):
        logger.debug("capture_frames started")
        frame_index = 0
        while self.tracking_active:
            if self.camera is None or not self.camera.isOpened():
                logger.warning("Camera not available. Attempting to reconnect.")
                self.reconnect_camera()
                continue
            # Grab a frame to clear the buffer without decoding
            if not self.camera.grab():
                logger.error("Failed to grab frame. Reconnecting...")
                self.reconnect_camera()
                continue
            frame_index += 1
            # Only decode and process every FRAME_SKIP-th frame
            if frame_index % config.FRAME_SKIP == 0:
                success, frame = self.camera.retrieve()
                if not success:
                    logger.error("Failed to retrieve frame. Reconnecting...")
                    self.reconnect_camera()
                    continue
                with self.lock:
                    self.frame_queue.append(frame)
            time.sleep(0.005)  # Slight sleep to prevent busy looping

    def process_frames(self):
        frame_count = 0
        frame_skip = config.FRAME_SKIP
        logger.debug("process_frames started")
        while self.tracking_active:
            with self.lock:
                if self.frame_queue:
                    frame = self.frame_queue.popleft()
                else:
                    time.sleep(0.01)
                    continue
            if frame_count % frame_skip == 0:
                try:
                    new_vehicles_count, annotated_frame = self.detector.detect_and_track(frame, frame_count)
                    self.total_car_count += new_vehicles_count
                    current_time = datetime.utcnow()
                    if new_vehicles_count > 0:
                        try:
                            with sqlite3.connect(config.DATABASE) as conn:
                                c = conn.cursor()
                                c.execute("""
                                    INSERT INTO traffic_data (timestamp, car_count)
                                    VALUES (?, ?)
                                """, (current_time.strftime('%Y-%m-%d %H:%M:%S'), new_vehicles_count))
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Database error: {e}")
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 35])
                    frame_data = base64.b64encode(buffer).decode('utf-8')
                    socketio.emit('frame', {
                        'frame': frame_data,
                        'car_count': new_vehicles_count,
                        'total_car_count': self.total_car_count,
                        'timestamp': current_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    })
                except Exception as e:
                    logger.error(f"Error processing frame: {e}")
                    traceback.print_exc()
            frame_count += 1

    def start(self):
        init_db()  # Initialize DB on start
        self.init_camera()
        self.tracking_active = True
        # Use SocketIO's start_background_task for better integration with eventlet
        self.capture_thread = socketio.start_background_task(self.capture_frames)
        self.process_thread = socketio.start_background_task(self.process_frames)
        logger.info("Traffic monitoring started.")

    def stop(self):
        self.tracking_active = False
        logger.info("Stopping traffic monitoring...")
        if self.camera:
            self.camera.release()
            self.camera = None
        logger.info("Traffic monitoring stopped.")

# Global instance of our monitor
traffic_monitor = TrafficMonitor()

@app.route('/')
def index():
    max_date = datetime.now().strftime('%Y-%m-%d')
    min_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('index.html', max_date=max_date, min_date=min_date)

@app.route('/tracking_status', methods=['GET'])
def tracking_status():
    return jsonify({'tracking_active': traffic_monitor.tracking_active})

@app.route('/historical_data', methods=['GET'])
def historical_data():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    granularity = request.args.get('granularity', default='60')
    try:
        start_date = parser.isoparse(start_date_str).astimezone(timezone.utc)
        end_date = parser.isoparse(end_date_str).astimezone(timezone.utc)
        if start_date >= end_date:
            return jsonify({'error': 'Start date must be before end date.'}), 400
        start_timestamp = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_timestamp = end_date.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use ISO 8601 format.'}), 400

    if granularity == '5':
        strftime_format = '%Y-%m-%d %H:%M:00'
    elif granularity == '30':
        strftime_format = '%Y-%m-%d %H:%M:00'
    elif granularity == '60':
        strftime_format = '%Y-%m-%d %H:00:00'
    else:
        return jsonify({'error': 'Invalid granularity value.'}), 400

    interval_delta = timedelta(minutes=int(granularity))
    intervals = []
    current = start_date
    while current < end_date:
        intervals.append(current)
        current += interval_delta

    try:
        with sqlite3.connect(config.DATABASE) as conn:
            conn.create_function('strftime', 2, lambda fmt, ts: datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime(fmt))
            c = conn.cursor()
            c.execute(f'''
                SELECT strftime('{strftime_format}', timestamp) as time,
                       SUM(car_count) as total_cars
                FROM traffic_data
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY time
                ORDER BY time
            ''', (start_timestamp, end_timestamp))
            data = c.fetchall()

        result = []
        data_dict = {row[0]: row[1] for row in data}
        for interval in intervals:
            interval_str = interval.strftime(strftime_format)
            car_count = data_dict.get(interval_str, 0)
            interval_iso = interval.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            result.append({'time': interval_iso, 'total_cars': car_count})

        return jsonify(result)
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error.'}), 500

@app.route('/start_tracking', methods=['POST'])
def start_tracking():
    if not traffic_monitor.tracking_active:
        traffic_monitor.start()
        return '', 204
    else:
        logger.info("Tracking already running.")
        return '', 409

@app.route('/stop_tracking', methods=['POST'])
def stop_tracking():
    if traffic_monitor.tracking_active:
        traffic_monitor.stop()
        return '', 204
    else:
        logger.info("Tracking is not running.")
        return '', 409

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        if traffic_monitor.camera:
            traffic_monitor.camera.release()
