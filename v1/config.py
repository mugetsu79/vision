import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Model paths configurable via environment variables (with defaults)
MODEL_PROTOTXT = os.getenv('MODEL_PROTOTXT', os.path.join(BASE_DIR, 'mobilenet_ssd_model', 'deploy.prototxt'))
MODEL_CAFFEMODEL = os.getenv('MODEL_CAFFEMODEL', os.path.join(BASE_DIR, 'mobilenet_ssd_model', 'mobilenet_iter_73000.caffemodel'))
LABELS_PATH = os.getenv('LABELS_PATH', os.path.join(BASE_DIR, 'mobilenet_ssd_model', 'coco_labels.txt'))

# RTSP stream URL
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://admin:787469@192.168.1.119:554/live/profile.1')

# Database file path
DATABASE = os.path.join(BASE_DIR, 'traffic.db')

# Frame skip interval
FRAME_SKIP = int(os.getenv('FRAME_SKIP', 3))

# Detection confidence threshold
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.2))

# Minimum bounding box size
MIN_WIDTH = int(os.getenv('MIN_WIDTH', 30))
MIN_HEIGHT = int(os.getenv('MIN_HEIGHT', 30))

# Margins for non-detection areas (now configurable)
MARGIN_TOP = int(os.getenv('MARGIN_TOP', 5))
MARGIN_BOTTOM = int(os.getenv('MARGIN_BOTTOM', 0))
MARGIN_LEFT = int(os.getenv('MARGIN_LEFT', 0))
MARGIN_RIGHT = int(os.getenv('MARGIN_RIGHT', 0))

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(levelname)s - %(message)s')
