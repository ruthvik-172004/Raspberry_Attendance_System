import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self, credential_path):
        """Initialize Firebase with the provided service account key."""
        self.cred = credentials.Certificate(credential_path)
        self.app = None
        self.db = None
        self.employees = {}
        self.logger = logging.getLogger(__name__)
        
        # Work hours configuration
        self.work_hours = {
            'start': datetime.time(9, 0),  # 9:00 AM
            'end': datetime.time(17, 0)    # 5:00 PM
        }
        
        # Late threshold in minutes
        self.late_threshold = 15
        
        # Store last attendance time for duplicate prevention
        self.last_attendance = {}
        
    def initialize(self):
        """Initialize Firebase app and Firestore client."""
        try:
            self.app = firebase_admin.initialize_app(self.cred)
            self.db = firestore.client()
            self.logger.info("Firebase initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing Firebase: {e}")
            return False
    
    def fetch_employee_encodings(self):
        """Fetch all employee face encodings from Firestore."""
        try:
            employees_ref = self.db.collection('employees')
            employees_docs = employees_ref.stream()
            
            self.employees = {}
            for doc in employees_docs:
                employee_data = doc.to_dict()
                
                # Skip employees without face encodings
                if 'face_encoding' not in employee_data:
                    continue
                
                # Store employee data with face encodings
                employee_id = employee_data.get('employeeID')
                if employee_id:
                    self.employees[employee_id] = {
                        'name': f"{employee_data.get('fname', '')} {employee_data.get('lname', '')}",
                        'department': employee_data.get('department', ''),
                        'position': employee_data.get('position', ''),
                        'face_encoding': employee_data.get('face_encoding', []),
                        'additional_face_encodings': employee_data.get('additional_face_encodings', [])
                    }
            
            self.logger.info(f"Fetched {len(self.employees)} employee records with face encodings")
            return self.employees
        except Exception as e:
            self.logger.error(f"Error fetching employee encodings: {e}")
            return {}
    
    def is_late_arrival(self, current_time=None):
        """Check if the current time is considered a late arrival."""
        if current_time is None:
            current_time = datetime.datetime.now().time()
            
        # Calculate start time plus threshold
        start_hour = self.work_hours['start'].hour
        start_minute = self.work_hours['start'].minute
        
        # Convert to minutes for easier comparison
        start_minutes = start_hour * 60 + start_minute
        current_minutes = current_time.hour * 60 + current_time.minute
        
        # Late if current time is after start time + threshold
        return current_minutes > (start_minutes + self.late_threshold)
    
    def mark_attendance_multi(self, recognized_employees):
        """Fast multi-employee attendance marking."""
        if not recognized_employees:
            return False, "No employees recognized", False, False
    
        current_time = datetime.datetime.now()
        current_timestamp = time.time()
    
        successful_checkins = []
    
        for emp in recognized_employees:
            employee_id = emp['employee_id']
            employee_name = emp['name']
        
            # Quick duplicate check
            if employee_id in self.last_attendance:
                time_diff = current_timestamp - self.last_attendance[employee_id]
                if time_diff < 30:  # 30 seconds cooldown
                    continue
    
            # Get employee data
            employee_data = self.employees.get(employee_id)
            if not employee_data:
                continue
    
            # Simple attendance record - always check-in for speed
            timestamp = current_time.isoformat()
            attendance_data = {
                'employeeID': employee_id,
                'name': employee_name,
                'timestamp': timestamp,
                'device': 'raspberry_pi_multi',
                'recordedAt': current_time,
                'type': 'check-in',
                'confidence': emp['confidence']
            }
        
            try:
                # Add to Firestore
                self.db.collection('attendance').add(attendance_data)
            
                # Update last attendance time
                self.last_attendance[employee_id] = current_timestamp
            
                successful_checkins.append(employee_name)
                self.logger.info(f"Quick check-in for {employee_name}")
            
            except Exception as e:
                self.logger.error(f"Error marking attendance for {employee_name}: {e}")
                continue
    
        if successful_checkins:
            if len(successful_checkins) == 1:
                message = f"Check-in marked for {successful_checkins[0]}"
            else:
                message = f"Check-in marked for {len(successful_checkins)} employees"
        
            return True, message, True, False
        else:
            return False, "No attendance marked", False, False

    def mark_attendance(self, employee_ids):
        """Legacy method for backward compatibility - converts to multi-face format."""
        if not employee_ids:
            return False, "No employees recognized", False, False
        
        # Convert legacy format to multi-face format
        recognized_employees = []
        for employee_id in employee_ids:
            employee_data = self.employees.get(employee_id, {})
            recognized_employees.append({
                'employee_id': employee_id,
                'name': employee_data.get('name', 'Unknown'),
                'confidence': 85.0,  # Default confidence for legacy calls
                'face_location': None,
                'face_index': 0
            })
        
        return self.mark_attendance_multi(recognized_employees)
