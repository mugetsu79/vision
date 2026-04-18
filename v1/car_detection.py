import cv2
import numpy as np
import config
import logging
from sort import Sort  # Import the SORT tracker

logger = logging.getLogger(__name__)

class CarDetector:
    def __init__(self):
        """
        Initialize the CarDetector with MobileNet SSD model and SORT tracker.
        """
        try:
            # Load the pre-trained MobileNet SSD model using configurable paths
            self.net = cv2.dnn.readNetFromCaffe(config.MODEL_PROTOTXT, config.MODEL_CAFFEMODEL)
            logger.debug("MobileNet SSD model loaded successfully.")

            # Load labels
            with open(config.LABELS_PATH, 'r') as f:
                self.labels = f.read().strip().split('\n')
            logger.debug(f"Labels loaded: {self.labels}")

            # Initialize SORT tracker
            self.tracker = Sort(max_age=30, min_hits=1, iou_threshold=0.2)
            logger.debug("SORT tracker initialized.")

            # Define a lock period in frames
            self.frame_lock_period = 30  # Adjust as needed
            self.last_frame_car_detected = None  # Initialize the last detected frame

            # Use configurable margins
            self.margin_top = config.MARGIN_TOP
            self.margin_bottom = config.MARGIN_BOTTOM
            self.margin_left = config.MARGIN_LEFT
            self.margin_right = config.MARGIN_RIGHT
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            self.net = None  # Ensure net is set to None if initialization fails

    def detect_and_track(self, img, frame_index):
        """
        Detect and track cars in a given image.

        Args:
            img (numpy.ndarray): Input image.
            frame_index (int): Index of the current frame.

        Returns:
            new_vehicles_count (int): Number of newly detected cars/trucks.
            annotated_frame (numpy.ndarray): Annotated image with bounding boxes.
        """
        if self.net is None:
            logger.error("Model is not initialized properly.")
            return 0, img

        try:
            # Preprocess the image
            #height, width = img.shape[:2]
            #roi = img[int(height/2):, :]
            blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)),
                                         0.007843, (300, 300), 127.5)
            self.net.setInput(blob)

            # Run the model
            detections = self.net.forward()
            annotated_frame = img.copy()
            new_vehicles_count = 0

            dets = []
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > config.CONFIDENCE_THRESHOLD:
                    idx = int(detections[0, 0, i, 1])
                    label = self.labels[idx] if idx < len(self.labels) else 'unknown'

                    if label in ['car', 'truck']:
                        box = detections[0, 0, i, 3:7] * np.array([
                            img.shape[1], img.shape[0], img.shape[1], img.shape[0]])
                        (startX, startY, endX, endY) = box.astype("int")

                        # Exclude detections within the configurable margins
                        if (startX < self.margin_left or
                            endX > img.shape[1] - self.margin_right or
                            startY < self.margin_top or
                            endY > img.shape[0] - self.margin_bottom):
                            logger.debug(f"Detection {i}: Ignored due to margin constraints")
                            continue

                        if ((endX - startX) > config.MIN_WIDTH and
                            (endY - startY) > config.MIN_HEIGHT):
                            dets.append([startX, startY, endX, endY, confidence])
                            cv2.rectangle(annotated_frame, (startX, startY),
                                          (endX, endY), color=(0, 255, 0), thickness=2)
                            label_text = f'{label.capitalize()}: {confidence:.2f}'
                            cv2.putText(annotated_frame, label_text,
                                        (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                        0.5, (0, 255, 0), 2)
                            logger.debug(f"Bounding box drawn for {label} with confidence {confidence:.2f}.")

            if dets:
                tracks = self.tracker.update(np.array(dets))
                logger.debug(f"Tracker updated with detections: {tracks}")

                # Global frame lock logic to avoid multiple counts within a short period
                if (self.last_frame_car_detected is None or
                    frame_index - self.last_frame_car_detected >= self.frame_lock_period):
                    new_vehicles_count += 1
                    self.last_frame_car_detected = frame_index
                    logger.debug(f"New vehicle detected at frame {frame_index}")
                else:
                    logger.debug(f"Frame lock active. Vehicle detection ignored at frame {frame_index}")

                # Annotate tracked objects
                for track in tracks:
                    x1, y1, x2, y2, track_id = track
                    logger.debug(f"Frame {frame_index}: Track ID: {track_id}, Bounding box: "
                                 f"({x1}, {y1}, {x2}, {y2})")
                    cv2.rectangle(annotated_frame, (int(x1), int(y1)),
                                  (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f'Car {int(track_id)}',
                                (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 255, 0), 2)
            else:
                logger.debug("No detections in this frame.")

            logger.info(f"Detected {new_vehicles_count} new cars in current frame")
            return new_vehicles_count, annotated_frame
        except Exception as e:
            logger.error(f"Error in detection and tracking: {e}")
            return 0, img
