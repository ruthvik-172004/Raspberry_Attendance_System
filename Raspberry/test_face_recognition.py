#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from face_recognition_utils_fixed import FaceRecognizer
from firebase_utils import FirebaseManager
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_face_recognition():
    """Test the face recognition system with fixed encoding handling."""
    
    print("🔍 Testing Face Recognition System...")
    
    # Initialize components
    face_recognizer = FaceRecognizer(
        "shape_predictor_68_face_landmarks.dat",
        "dlib_face_recognition_resnet_model_v1.dat",
        threshold=0.5
    )
    
    firebase = FirebaseManager("serviceAccountKey.json")
    if not firebase.initialize():
        print("❌ Firebase initialization failed")
        return False
    
    # Fetch employee encodings
    print("📥 Fetching employee encodings...")
    employee_encodings = firebase.fetch_employee_encodings()
    
    if not employee_encodings:
        print("❌ No employee encodings found")
        return False
    
    print(f"✅ Found {len(employee_encodings)} employee records")
    
    # Test encoding conversion
    print("🔧 Testing encoding conversion...")
    for emp_id, emp_data in employee_encodings.items():
        encoding = emp_data.get('face_encoding', [])
        converted = face_recognizer._convert_encoding_to_array(encoding)
        
        if converted is not None:
            print(f"✅ {emp_id}: Encoding converted successfully (shape: {converted.shape})")
        else:
            print(f"❌ {emp_id}: Failed to convert encoding")
    
    print("✅ Face recognition test completed!")
    return True

if __name__ == "__main__":
    test_face_recognition()
