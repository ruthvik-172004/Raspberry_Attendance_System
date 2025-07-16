import dlib
import numpy as np
import cv2
import logging
import math
import json
import ast

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self, shape_predictor_path, face_rec_model_path, threshold=0.5):
        self.logger = logging.getLogger(__name__)

        try:
            self.detector = dlib.get_frontal_face_detector()
            self.logger.info("Face detector loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading face detector: {e}")
            self.detector = None

        try:
            self.shape_predictor = dlib.shape_predictor(shape_predictor_path)
            self.face_rec_model = dlib.face_recognition_model_v1(face_rec_model_path)
            self.logger.info("Face recognition models loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading face recognition models: {e}")
            self.shape_predictor = None
            self.face_rec_model = None

        self.threshold = threshold
        self.logger.info(f"Face recognition threshold set to {threshold}")

    def _convert_encoding_to_array(self, encoding):
        """Convert various encoding formats to numpy array."""
        try:
            # If it's already a numpy array, return as is
            if isinstance(encoding, np.ndarray):
                return encoding.astype(np.float64)
            
            # If it's a list, convert to numpy array
            if isinstance(encoding, list):
                return np.array(encoding, dtype=np.float64)
            
            # If it's a string representation of a list/array
            if isinstance(encoding, str):
                # Try to parse as JSON first
                try:
                    parsed = json.loads(encoding)
                    return np.array(parsed, dtype=np.float64)
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Try to parse as Python literal
                try:
                    parsed = ast.literal_eval(encoding)
                    return np.array(parsed, dtype=np.float64)
                except (ValueError, SyntaxError):
                    pass
                
                # If it looks like a numpy array string representation
                if encoding.startswith('[') and encoding.endswith(']'):
                    # Remove brackets and split by comma
                    values_str = encoding.strip('[]')
                    values = [float(x.strip()) for x in values_str.split(',')]
                    return np.array(values, dtype=np.float64)
            
            # If none of the above work, log error and return None
            self.logger.error(f"Could not convert encoding to array: {type(encoding)}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting encoding to array: {e}")
            return None

    def detect_faces(self, image):
        """Fast face detection optimized for real-time processing."""
        if self.detector is None or image is None:
            return []
        try:
            if image.size == 0 or len(image.shape) < 2:
                return []

            # Convert to grayscale for detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
            # Single pass detection for speed
            dlib_faces = self.detector(gray, 0)  # 0 upsampling for maximum speed
        
            return list(dlib_faces)
        except Exception as e:
            self.logger.error(f"Error detecting faces: {e}")
            return []

    def align_face(self, image, face):
        try:
            # Ensure image is grayscale for shape predictor
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            shape = self.shape_predictor(gray, face)

            left_eye = np.mean([(shape.part(i).x, shape.part(i).y) for i in range(36, 42)], axis=0)
            right_eye = np.mean([(shape.part(i).x, shape.part(i).y) for i in range(42, 48)], axis=0)

            dx = right_eye[0] - left_eye[0]
            dy = right_eye[1] - left_eye[1]
            angle = math.degrees(math.atan2(dy, dx))

            center = (face.left() + face.width() // 2, face.top() + face.height() // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1)
            aligned_face = cv2.warpAffine(image, M, (image.shape[1], image.shape[0]), flags=cv2.INTER_CUBIC)

            return aligned_face
        except Exception as e:
            self.logger.error(f"Error aligning face: {e}")
            return image

    def get_face_encoding(self, image, face):
        """Get face encoding with proper image format handling."""
        if self.shape_predictor is None or self.face_rec_model is None:
            return None
        try:
            # Ensure we have a 3-channel BGR image for dlib face recognition
            if len(image.shape) == 2:
                # Convert grayscale to BGR
                image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif image.shape[2] == 3:
                # Already 3-channel, use as is
                image_bgr = image
            else:
                self.logger.error(f"Unsupported image format: {image.shape}")
                return None
            
            # Align face
            aligned_image = self.align_face(image_bgr, face)
            
            # Get shape landmarks using grayscale
            if len(aligned_image.shape) == 3:
                gray = cv2.cvtColor(aligned_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = aligned_image
                
            shape = self.shape_predictor(gray, face)
            
            # Compute face descriptor using 3-channel image
            face_encoding = self.face_rec_model.compute_face_descriptor(aligned_image, shape, 3)
            encoding = np.array(face_encoding, dtype=np.float64)
            
            if len(encoding) != 128:
                self.logger.error(f"Invalid encoding length: {len(encoding)}")
                return None
                
            return encoding
        except Exception as e:
            self.logger.error(f"Error extracting face encoding: {e}")
            return None

    def get_face_encoding_fast(self, image, face):
        """Fast face encoding without alignment for speed."""
        if self.shape_predictor is None or self.face_rec_model is None:
            return None
        try:
            # Ensure we have a 3-channel BGR image
            if len(image.shape) == 2:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif image.shape[2] == 3:
                image_bgr = image
            else:
                return None
            
            # Get shape landmarks using grayscale
            if len(image_bgr.shape) == 3:
                gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_bgr
                
            shape = self.shape_predictor(gray, face)
            
            # Compute face descriptor using 3-channel image with reduced jittering
            face_encoding = self.face_rec_model.compute_face_descriptor(image_bgr, shape, 1)
            encoding = np.array(face_encoding, dtype=np.float64)
        
            if len(encoding) != 128:
                return None
            return encoding
        except Exception as e:
            self.logger.error(f"Error extracting fast face encoding: {e}")
            return None

    def get_face_encodings(self, image):
        """Detect all faces and return list of encodings with face locations."""
        faces = self.detect_faces(image)
        face_data = []
        
        for i, face in enumerate(faces):
            encoding = self.get_face_encoding(image, face)
            if encoding is not None:
                face_data.append({
                    'encoding': encoding,
                    'location': face,
                    'index': i,
                    'area': face.width() * face.height()
                })
        
        # Sort by face area (largest first) for consistent processing
        face_data.sort(key=lambda x: x['area'], reverse=True)
        
        return face_data

    def compare_face_encodings(self, encoding1, encoding2):
        try:
            # Convert both encodings to proper numpy arrays
            enc1 = self._convert_encoding_to_array(encoding1)
            enc2 = self._convert_encoding_to_array(encoding2)
            
            if enc1 is None or enc2 is None:
                self.logger.error("Failed to convert one or both encodings to arrays")
                return False, 1.0
            
            # Validate encoding dimensions
            if enc1.shape[0] != 128 or enc2.shape[0] != 128:
                self.logger.error(f"Invalid encoding dimensions: {enc1.shape[0]}, {enc2.shape[0]}")
                return False, 1.0
            
            # Calculate Euclidean distance
            distance = np.linalg.norm(enc1 - enc2)
            is_match = distance < self.threshold
            
            self.logger.debug(f"Face comparison - Distance: {distance:.4f}, Threshold: {self.threshold}, Match: {is_match}")
            
            return is_match, distance
            
        except Exception as e:
            self.logger.error(f"Error comparing face encodings: {e}")
            return False, 1.0

    def find_matching_employee(self, face_encoding, employee_encodings):
        """Find matching employee for a single face encoding."""
        best_match = None
        best_distance = float('inf')

        for employee_id, employee_data in employee_encodings.items():
            # Get primary encoding
            primary_encoding = employee_data.get("face_encoding", [])
            additional_encodings = employee_data.get("additional_face_encodings", [])
            
            # Combine all encodings for this employee
            all_encodings = [primary_encoding] + additional_encodings
            
            for encoding in all_encodings:
                if not encoding:  # Skip empty encodings
                    continue
                    
                try:
                    is_match, distance = self.compare_face_encodings(face_encoding, encoding)
                    if is_match and distance < best_distance:
                        best_match = employee_id
                        best_distance = distance
                        self.logger.debug(f"Found match for {employee_id} with distance {distance:.4f}")
                        
                except Exception as e:
                    self.logger.error(f"Error comparing with encoding for {employee_id}: {e}")

        if best_match:
            self.logger.info(f"Best match: {best_match} with distance {best_distance:.4f}")
        
        return best_match, best_distance

    def find_all_matching_employees(self, image, employee_encodings):
        """Fast multi-face recognition optimized for real-time processing."""
        faces = self.detect_faces(image)
        recognized_employees = []
    
        if not faces:
            return recognized_employees
    
        self.logger.info(f"Processing {len(faces)} faces")
    
        # Process up to 3 faces maximum for speed
        faces_to_process = faces[:3]
    
        for i, face in enumerate(faces_to_process):
            try:
                # Get face encoding with proper format handling
                encoding = self.get_face_encoding_fast(image, face)
                if encoding is None:
                    self.logger.warning(f"Failed to get encoding for face {i}")
                    continue
            
                # Find matching employee
                employee_id, distance = self.find_matching_employee(encoding, employee_encodings)
            
                if employee_id and distance < self.threshold:
                    # Check if already recognized
                    already_recognized = any(emp['employee_id'] == employee_id for emp in recognized_employees)
                
                    if not already_recognized:
                        employee_data = employee_encodings.get(employee_id, {})
                        confidence = max(0, min(100, (1 - distance) * 100))
                    
                        # Accept matches with reasonable confidence
                        if confidence > 60:  # Lowered threshold for better recognition
                            recognized_employees.append({
                                'employee_id': employee_id,
                                'name': employee_data.get('name', 'Unknown'),
                                'distance': distance,
                                'face_location': face,
                                'face_index': i,
                                'confidence': confidence
                            })
                        
                            self.logger.info(f"Recognized: {employee_data.get('name', 'Unknown')} (Confidence: {confidence:.1f}%)")
                        else:
                            self.logger.info(f"Low confidence match for {employee_data.get('name', 'Unknown')}: {confidence:.1f}%")
                    else:
                        self.logger.info(f"Employee {employee_id} already recognized, skipping duplicate")
                else:
                    self.logger.info(f"Face {i+1} not recognized (distance: {distance:.3f}, threshold: {self.threshold})")
            except Exception as e:
                self.logger.error(f"Error processing face {i}: {e}")
                continue
    
        return recognized_employees

    def draw_face_rectangle(self, image, face, label="Face Detected", color=(0, 255, 0)):
        """Draw rectangle around face with optional label."""
        try:
            x, y, w, h = face.left(), face.top(), face.width(), face.height()
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            
            # Draw label with background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(image, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
            cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return image
        except Exception as e:
            self.logger.error(f"Error drawing face rectangle: {e}")
            return image

    def draw_all_faces(self, image, recognized_employees):
        """Draw rectangles around all recognized faces with names."""
        try:
            result_image = image.copy()
            
            for emp in recognized_employees:
                face_location = emp['face_location']
                name = emp['name']
                confidence = emp['confidence']
                
                # Color based on confidence
                if confidence > 80:
                    color = (0, 255, 0)  # Green for high confidence
                elif confidence > 60:
                    color = (0, 255, 255)  # Yellow for medium confidence
                else:
                    color = (0, 165, 255)  # Orange for low confidence
                
                label = f"{name} ({confidence:.0f}%)"
                result_image = self.draw_face_rectangle(result_image, face_location, label, color)
            
            return result_image
        except Exception as e:
            self.logger.error(f"Error drawing all faces: {e}")
            return image
