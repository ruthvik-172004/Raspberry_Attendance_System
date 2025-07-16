import os
import sys
import time
import cv2
import numpy as np
import argparse
import logging
import traceback
import threading
import pickle
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# Custom module imports
from camera_utils import CameraManager
from face_recognition_utils import FaceRecognizer
from firebase_utils import FirebaseManager
from ui_utils import UIManager
from hardware_utils import HardwareManager
from speech_utils import SpeechManager

# Default paths
SHAPE_PREDICTOR_PATH = "shape_predictor_68_face_landmarks.dat"
FACE_REC_MODEL_PATH = "dlib_face_recognition_resnet_model_v1.dat"
FIREBASE_CREDENTIALS_PATH = "serviceAccountKey.json"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Raspberry Pi Multi-Face Recognition Attendance System')
    parser.add_argument('--shape-predictor', type=str, default=SHAPE_PREDICTOR_PATH)
    parser.add_argument('--face-rec-model', type=str, default=FACE_REC_MODEL_PATH)
    parser.add_argument('--firebase-credentials', type=str, default=FIREBASE_CREDENTIALS_PATH)
    parser.add_argument('--threshold', type=float, default=0.5)
    parser.add_argument('--resolution', type=str, default='320x240')  # Faster resolution
    parser.add_argument('--framerate', type=int, default=30)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--green-led-pin', type=int, default=17)
    parser.add_argument('--red-led-pin', type=int, default=27)
    parser.add_argument('--no-speech', action='store_true')
    parser.add_argument('--no-leds', action='store_true')
    parser.add_argument('--multi-face', action='store_true', default=True, help='Enable multi-face recognition')
    return parser.parse_args()

def control_led(hardware, led_type, duration=2):
    if led_type == 'green':
        threading.Thread(target=hardware.green_led_on, args=(duration,), daemon=True).start()
    elif led_type == 'red':
        threading.Thread(target=hardware.red_led_on, args=(duration,), daemon=True).start()

def main():
    args = parse_arguments()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")

    try:
        width, height = map(int, args.resolution.split('x'))
        resolution = (width, height)
    except:
        logger.warning(f"Invalid resolution format: {args.resolution}. Using default 640x480.")
        resolution = (640, 480)

    # Model checks
    if not os.path.exists(args.shape_predictor) or not os.path.exists(args.face_rec_model):
        logger.error("Model files missing.")
        return
    if not os.path.exists(args.firebase_credentials):
        logger.error("Firebase credentials missing.")
        return

    logger.info("Initializing multi-face recognition system...")

    camera = CameraManager(resolution=resolution, framerate=args.framerate)
    if not camera.initialize():
        return

    face_recognizer = FaceRecognizer(args.shape_predictor, args.face_rec_model, threshold=args.threshold)
    firebase = FirebaseManager(args.firebase_credentials)
    if not firebase.initialize():
        camera.close()
        return

    hardware = None
    if not args.no_leds:
        hardware = HardwareManager(args.green_led_pin, args.red_led_pin)
        if not hardware.initialize():
            hardware = None

    speech = None
    if not args.no_speech:
        speech = SpeechManager()
        if not speech.initialize():
            speech = None

    # Load face encodings from pkl or Firebase
    employee_encodings = {}
    try:
        with open("encodings.pkl", "rb") as f:
            encodings_list = pickle.load(f)
            employee_encodings = {
                f"emp_{i}": {
                    "name": data["name"],
                    "department": "Test",
                    "position": "Test",
                    "face_encoding": data["encoding"],
                    "additional_face_encodings": []
                } for i, data in enumerate(encodings_list)
            }
        logger.info(f"Loaded {len(employee_encodings)} encodings from encodings.pkl")
    except Exception as e:
        logger.warning(f"Could not load encodings.pkl: {e}")
        logger.info("Falling back to Firebase...")
        employee_encodings = firebase.fetch_employee_encodings()

    if not employee_encodings:
        logger.warning("No encodings found. Please register faces.")
        camera.close()
        if hardware: hardware.cleanup()
        if speech: speech.cleanup()
        return

    ui = UIManager(resolution=resolution)
    if not ui.initialize_window():
        camera.close()
        if hardware: hardware.cleanup()
        if speech: speech.cleanup()
        return

    logger.info("Multi-face recognition system ready.")
    if speech:
        speech.speak("Multi-face attendance system ready. Multiple people can be recognized simultaneously.")

    running = True
    last_recognition_time = 0
    recognition_cooldown = 2  # Reduced from 3 seconds
    current_message = None
    message_display_time = 0
    message_duration = 4  # Longer duration for multi-face messages

    while running:
        try:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.5)
                continue

            current_time = time.time()

            if current_message and current_time - message_display_time < message_duration:
                if current_message['type'] == 'success':
                    frame = ui.show_success_message(frame, current_message['employee_name'], current_message['message'])
                else:
                    frame = ui.show_error_message(frame, current_message['message'])
            else:
                current_message = None

                if current_time - last_recognition_time > recognition_cooldown:
                    # Always use optimized multi-face recognition
                    recognized_employees = face_recognizer.find_all_matching_employees(frame, employee_encodings)
                    
                    if recognized_employees:
                        # Draw rectangles for recognized faces
                        for emp in recognized_employees:
                            face_location = emp['face_location']
                            name = emp['name']
                            confidence = emp['confidence']
                            
                            # Simple green rectangle for recognized faces
                            frame = face_recognizer.draw_face_rectangle(frame, face_location, f"{name} ({confidence:.0f}%)", (0, 255, 0))
                        
                        # Mark attendance
                        success, message, is_check_in, is_late = firebase.mark_attendance_multi(recognized_employees)
                        
                        if success:
                            if len(recognized_employees) == 1:
                                employee_name = recognized_employees[0]['name']
                            else:
                                employee_name = f"{len(recognized_employees)} employees"
                            
                            current_message = {
                                'type': 'success',
                                'employee_name': employee_name,
                                'message': message
                            }

                            if speech:
                                if len(recognized_employees) == 1:
                                    speech.speak(f"Hi {recognized_employees[0]['name']}. Attendance marked.")
                                else:
                                    speech.speak(f"Attendance marked for {len(recognized_employees)} employees")

                            if hardware:
                                control_led(hardware, 'green', duration=2)
                        else:
                            current_message = {'type': 'error', 'message': message}
                            if hardware:
                                control_led(hardware, 'red', duration=1)
                    else:
                        # Check for unknown faces
                        faces = face_recognizer.detect_faces(frame)
                        if faces:
                            # Draw red rectangles for unknown faces
                            for face in faces:
                                frame = face_recognizer.draw_face_rectangle(frame, face, "Unknown", (0, 0, 255))
                            
                            current_message = {'type': 'error', 'message': f"{len(faces)} unknown face(s)"}
                            if hardware:
                                control_led(hardware, 'red', duration=1)
                        else:
                            frame = ui.overlay_text(frame, "Show your face to the camera", position=(30, 30))

                    last_recognition_time = current_time
                    if current_message:
                        message_display_time = current_time

            ui.show_frame(frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                running = False
            elif key == ord('r'):
                employee_encodings = firebase.fetch_employee_encodings()
                logger.info(f"Reloaded {len(employee_encodings)} employee records.")
                if speech:
                    speech.speak(f"Employee data refreshed. {len(employee_encodings)} records loaded.")
            elif key == ord('m'):
                args.multi_face = not args.multi_face
                mode = "multi-face" if args.multi_face else "single-face"
                logger.info(f"Switched to {mode} recognition mode")
                if speech:
                    speech.speak(f"Switched to {mode} mode")

        except KeyboardInterrupt:
            running = False
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            if args.debug:
                logger.error(traceback.format_exc())
            time.sleep(1)

    logger.info("Cleaning up...")
    camera.close()
    ui.close_window()
    if hardware: hardware.cleanup()
    if speech: speech.cleanup()

if __name__== "__main__":
    main()
