#!/usr/bin/env python3

import json
import numpy as np
from firebase_utils import FirebaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_firebase_encodings():
    """Fix face encodings in Firebase that are stored as strings."""
    
    # Initialize Firebase
    firebase = FirebaseManager("serviceAccountKey.json")
    if not firebase.initialize():
        logger.error("Failed to initialize Firebase")
        return False
    
    try:
        # Get all employees
        employees_ref = firebase.db.collection('employees')
        employees_docs = employees_ref.stream()
        
        fixed_count = 0
        
        for doc in employees_docs:
            employee_data = doc.to_dict()
            employee_id = doc.id
            
            # Check if face_encoding exists and is a string
            if 'face_encoding' in employee_data:
                encoding = employee_data['face_encoding']
                
                # If it's a string, try to convert it to a list
                if isinstance(encoding, str):
                    try:
                        # Parse the string as JSON
                        if encoding.startswith('[') and encoding.endswith(']'):
                            parsed_encoding = json.loads(encoding)
                            
                            # Update the document
                            doc.reference.update({
                                'face_encoding': parsed_encoding
                            })
                            
                            logger.info(f"Fixed encoding for employee {employee_id}")
                            fixed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to fix encoding for {employee_id}: {e}")
                
                # Also fix additional_face_encodings if they exist
                if 'additional_face_encodings' in employee_data:
                    additional = employee_data['additional_face_encodings']
                    if isinstance(additional, list):
                        fixed_additional = []
                        for add_enc in additional:
                            if isinstance(add_enc, str):
                                try:
                                    parsed = json.loads(add_enc)
                                    fixed_additional.append(parsed)
                                except:
                                    fixed_additional.append(add_enc)
                            else:
                                fixed_additional.append(add_enc)
                        
                        # Update if any changes were made
                        if fixed_additional != additional:
                            doc.reference.update({
                                'additional_face_encodings': fixed_additional
                            })
                            logger.info(f"Fixed additional encodings for employee {employee_id}")
        
        logger.info(f"Fixed {fixed_count} employee encodings")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing Firebase encodings: {e}")
        return False

if __name__ == "__main__":
    fix_firebase_encodings()
