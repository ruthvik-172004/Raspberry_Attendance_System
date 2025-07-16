import cv2
import numpy as np
import logging
from PIL import Image, ImageDraw, ImageFont
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UIManager:
    def __init__(self, resolution=(640, 480)):
        """Initialize UI manager with specified resolution."""
        self.logger = logging.getLogger(__name__)
        self.resolution = resolution
        self.window_name = "Face Recognition Attendance System"
        self.font = None
        self._load_font()
        
    def _load_font(self):
        """Load a font for text rendering."""
        try:
            # Try to load a system font
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "C:/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self.font = ImageFont.truetype(font_path, 20)
                    self.logger.info(f"Loaded font from {font_path}")
                    break
            
            if self.font is None:
                self.font = ImageFont.load_default()
                self.logger.warning("Using default font")
                
        except Exception as e:
            self.logger.error(f"Error loading font: {e}")
            self.font = ImageFont.load_default()
    
    def initialize_window(self):
        """Initialize the display window."""
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            self.logger.info("Display window initialized")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing window: {e}")
            return False
    
    def show_frame(self, frame):
        """Display a frame in the window."""
        try:
            if frame is not None:
                cv2.imshow(self.window_name, frame)
        except Exception as e:
            self.logger.error(f"Error displaying frame: {e}")
    
    def overlay_text(self, frame, text, position=(30, 30), color=(255, 255, 255), bg_color=None, font_scale=0.7):
        """Overlay text on the frame."""
        try:
            if bg_color:
                # Calculate text size for background
                (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
                
                # Draw background rectangle
                cv2.rectangle(frame, 
                            (position[0] - 5, position[1] - text_height - 5),
                            (position[0] + text_width + 5, position[1] + baseline + 5),
                            bg_color, -1)
            
            # Draw text
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)
            
            return frame
        except Exception as e:
            self.logger.error(f"Error overlaying text: {e}")
            return frame
    
    def show_success_message(self, frame, employee_name, message):
        """Show success message overlay."""
        try:
            # Green background for success
            frame = self.overlay_text(frame, f"Welcome {employee_name}!", 
                                    position=(30, 50), 
                                    color=(255, 255, 255), 
                                    bg_color=(0, 150, 0),
                                    font_scale=0.8)
            
            frame = self.overlay_text(frame, message, 
                                    position=(30, 90), 
                                    color=(255, 255, 255), 
                                    bg_color=(0, 150, 0),
                                    font_scale=0.6)
            
            return frame
        except Exception as e:
            self.logger.error(f"Error showing success message: {e}")
            return frame
    
    def show_error_message(self, frame, message):
        """Show error message overlay."""
        try:
            # Red background for error
            frame = self.overlay_text(frame, message, 
                                    position=(30, 50), 
                                    color=(255, 255, 255), 
                                    bg_color=(0, 0, 200),
                                    font_scale=0.7)
            
            return frame
        except Exception as e:
            self.logger.error(f"Error showing error message: {e}")
            return frame
    
    def close_window(self):
        """Close the display window."""
        try:
            cv2.destroyAllWindows()
            self.logger.info("Display window closed")
        except Exception as e:
            self.logger.error(f"Error closing window: {e}")

    def save_frame(self, frame, file_path):
        """Save the frame to a file."""
        try:
            cv2.imwrite(file_path, frame)
            self.logger.info(f"Frame saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving frame: {e}")

    def resize_frame(self, frame, new_resolution):
        """Resize the frame to a new resolution."""
        try:
            resized_frame = cv2.resize(frame, new_resolution)
            self.logger.info(f"Frame resized to {new_resolution}")
            return resized_frame
        except Exception as e:
            self.logger.error(f"Error resizing frame: {e}")
            return frame
