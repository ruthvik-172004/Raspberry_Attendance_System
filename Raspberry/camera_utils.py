import cv2
import numpy as np
import logging
from picamera2 import Picamera2
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CameraManager:
    def __init__(self, resolution=(320, 240), framerate=15):  # Reduced for speed
        """Initialize camera manager with specified resolution and framerate."""
        self.logger = logging.getLogger(__name__)
        self.resolution = resolution
        self.framerate = framerate
        self.camera = None
        self.frame_count = 0
        
    def initialize(self):
        """Initialize the Picamera2."""
        try:
            self.camera = Picamera2()
        
            # Configure camera with basic settings only
            config = self.camera.create_preview_configuration(
                main={"format": "RGB888", "size": self.resolution},
                controls={"FrameRate": self.framerate},
                buffer_count=2  # Reduce buffer for lower latency
            )
        
            self.camera.configure(config)
        
            # Start camera
            self.camera.start()
        
            # Wait for camera to warm up
            time.sleep(2)
        
            self.logger.info("Camera initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False

    
    def get_frame(self):
        """Get a single frame from the camera with optimized speed."""
        if not self.camera:
            self.logger.error("Camera not initialized")
            return None

        try:
            # Capture raw RGB frame directly
            frame = self.camera.capture_array()

            if frame is None or frame.size == 0:
                return None

            # Minimal processing for speed
            # Convert to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Rotate frame 180° to correct upside-down camera
            frame = cv2.rotate(frame, cv2.ROTATE_180)

            return frame

        except Exception as e:
            self.logger.error(f"Error getting frame: {e}")
            return None

    def apply_white_balance(self, frame):
        """Apply simple white balance correction for better color accuracy."""
        try:
            # Calculate average values for each channel
            avg_b = np.mean(frame[:, :, 2])  # Blue channel in RGB
            avg_g = np.mean(frame[:, :, 1])  # Green channel
            avg_r = np.mean(frame[:, :, 0])  # Red channel
    
            # Calculate scaling factors
            avg_gray = (avg_r + avg_g + avg_b) / 3
    
            scale_r = avg_gray / avg_r if avg_r > 0 else 1
            scale_g = avg_gray / avg_g if avg_g > 0 else 1
            scale_b = avg_gray / avg_b if avg_b > 0 else 1
        
            # Apply scaling with limits to prevent over-correction
            scale_r = np.clip(scale_r, 0.5, 2.0)
            scale_g = np.clip(scale_g, 0.5, 2.0)
            scale_b = np.clip(scale_b, 0.5, 2.0)
        
            # Apply white balance
            frame[:, :, 0] = np.clip(frame[:, :, 0] * scale_r, 0, 255)  # Red
            frame[:, :, 1] = np.clip(frame[:, :, 1] * scale_g, 0, 255)  # Green
            frame[:, :, 2] = np.clip(frame[:, :, 2] * scale_b, 0, 255)  # Blue
        
            return frame.astype(np.uint8)
        except Exception as e:
            self.logger.error(f"Error applying white balance: {e}")
            return frame

    def _enhance_image(self, image):
        """Apply basic image enhancement."""
        try:
            # Apply slight sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(image, -1, kernel)
        
            # Blend original and sharpened (subtle effect)
            enhanced = cv2.addWeighted(image, 0.7, sharpened, 0.3, 0)
        
            return enhanced
        
        except Exception as e:
            self.logger.error(f"Error enhancing image: {e}")
            return image
    
    def close(self):
        """Close the camera."""
        try:
            if self.camera:
                self.camera.stop()
                self.camera.close()
                self.logger.info("Camera closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing camera: {e}")
