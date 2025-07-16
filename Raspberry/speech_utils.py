import pyttsx3
import threading
import logging
import os
import subprocess
import tempfile
from gtts import gTTS

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpeechManager:
    def __init__(self, use_pyttsx3=True):
        """Initialize text-to-speech engine."""
        self.logger = logging.getLogger(__name__)
        self.use_pyttsx3 = use_pyttsx3
        self.engine = None
        self.speaking = False
        self.speech_thread = None
        
    def initialize(self):
        """Initialize the text-to-speech engine."""
        if self.use_pyttsx3:
            try:
                self.engine = pyttsx3.init()
                # Set properties
                self.engine.setProperty('rate', 150)  # Speed of speech
                self.engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
                
                # Get available voices and set to a female voice if available
                voices = self.engine.getProperty('voices')
                for voice in voices:
                    if "female" in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                
                self.logger.info("Text-to-speech engine initialized successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error initializing pyttsx3: {e}")
                self.use_pyttsx3 = False
                self.logger.info("Falling back to gTTS")
        
        # If pyttsx3 failed or was not selected, we'll use gTTS when needed
        self.logger.info("Using gTTS for text-to-speech")
        return True
    
    def speak(self, text):
        """Speak the given text using the initialized engine."""
        if self.speaking:
            self.logger.info("Already speaking, ignoring new request")
            return False
        
        # Start speech in a separate thread to avoid blocking
        self.speech_thread = threading.Thread(target=self._speak_thread, args=(text,))
        self.speech_thread.daemon = True
        self.speech_thread.start()
        return True
    
    def _speak_thread(self, text):
        """Internal method to handle speech in a separate thread."""
        self.speaking = True
        
        try:
            if self.use_pyttsx3 and self.engine:
                self.logger.info(f"Speaking with pyttsx3: '{text}'")
                self.engine.say(text)
                self.engine.runAndWait()
            else:
                self.logger.info(f"Speaking with gTTS: '{text}'")
                # Use gTTS and mpg123 to play the speech
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_filename = temp_file.name
                
                # Create the speech MP3
                tts = gTTS(text=text, lang='en')
                tts.save(temp_filename)
                
                # Play the MP3
                subprocess.call(['mpg123', '-q', temp_filename])
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_filename)
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {e}")
        
        self.speaking = False
    
    def is_speaking(self):
        """Check if the engine is currently speaking."""
        return self.speaking
    
    def wait_until_done(self):
        """Wait until the current speech is complete."""
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join()
    
    def cleanup(self):
        """Clean up resources."""
        if self.speaking:
            self.wait_until_done()
        
        if self.use_pyttsx3 and self.engine:
            try:
                self.engine.stop()
            except:
                pass
        
        self.logger.info("Text-to-speech resources cleaned up")
        return True
