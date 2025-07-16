import RPi.GPIO as GPIO
import time
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HardwareManager:
    def __init__(self, green_led_pin=17, red_led_pin=27):
        """Initialize hardware manager with LED pins."""
        self.logger = logging.getLogger(__name__)
        self.green_led_pin = green_led_pin
        self.red_led_pin = red_led_pin
        self.initialized = False
        
    def initialize(self):
        """Initialize GPIO pins for LEDs."""
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup LED pins
            GPIO.setup(self.green_led_pin, GPIO.OUT)
            GPIO.setup(self.red_led_pin, GPIO.OUT)
            
            # Turn off LEDs initially
            GPIO.output(self.green_led_pin, GPIO.LOW)
            GPIO.output(self.red_led_pin, GPIO.LOW)
            
            self.initialized = True
            self.logger.info("Hardware components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing hardware: {e}")
            return False
    
    def green_led_on(self, duration=2):
        """Turn on green LED for specified duration."""
        if not self.initialized:
            return
            
        try:
            GPIO.output(self.green_led_pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(self.green_led_pin, GPIO.LOW)
        except Exception as e:
            self.logger.error(f"Error controlling green LED: {e}")
    
    def red_led_on(self, duration=2):
        """Turn on red LED for specified duration."""
        if not self.initialized:
            return
            
        try:
            GPIO.output(self.red_led_pin, GPIO.HIGH)
            time.sleep(duration)
            GPIO.output(self.red_led_pin, GPIO.LOW)
        except Exception as e:
            self.logger.error(f"Error controlling red LED: {e}")
    
    def cleanup(self):
        """Clean up GPIO resources."""
        try:
            if self.initialized:
                GPIO.cleanup()
                self.logger.info("Hardware resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up hardware: {e}")

    def blink_led(self, pin, duration=1, interval=0.5):
        """Blink an LED on a specified pin."""
        if not self.initialized:
            return
        
        try:
            end_time = time.time() + duration
            while time.time() < end_time:
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(interval)
                GPIO.output(pin, GPIO.LOW)
                time.sleep(interval)
        except Exception as e:
            self.logger.error(f"Error blinking LED on pin {pin}: {e}")

    def toggle_led(self, pin):
        """Toggle an LED on a specified pin."""
        if not self.initialized:
            return
        
        try:
            current_state = GPIO.input(pin)
            GPIO.output(pin, not current_state)
        except Exception as e:
            self.logger.error(f"Error toggling LED on pin {pin}: {e}")
