import face_recognition
import cv2
from datetime import datetime
import os
import json
import firebase_admin
from firebase_admin import firestore, credentials


def initialize_firestore():
    # Initialize Firestore
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    return db

def findEncodings(images):
    encodeList = []

    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

def read_json_file(file_path):
    """
    Read JSON data from a file.
    
    Args:
    - file_path: Path to the JSON file.
    
    Returns:
    - data: JSON data read from the file.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def get_date_and_count_from_attendance_data(attendence_doc):
    # Extract the keys
    year = list(attendence_doc.keys())[0]
    month = list(attendence_doc[year].keys())[0]
    print(f"day list: {attendence_doc[year][month].keys()}")
    day = list(attendence_doc[year][month].keys())[-1]
    count = list(attendence_doc[year][month].keys())[0]

    # Construct the desired string
    date_string = f"{year}-{month}-{day}"
    return date_string, count


def markAttendance(name, db):
    current_time = datetime.now().strftime("%H:%M:%S")
    """
    Record attendance in Firestore.
    """
    # Get today's date
    # TODO: need the data for time
    today = datetime.now().strftime("%Y-%m-%d")
    temp_list_attendence = {}
    today = datetime.now().strftime("%Y-%m-%d")
    split_today = today.split(sep="-")
    print(split_today[0])
    attendance_data = {
            split_today[0]: {
                split_today[1]: {
                    'count': 1,
                    split_today[2]: {
                        'check_in_time': current_time
                    }
                }
            }
        }
    teacher_ids = get_teacher_ids()
    user_id = teacher_ids[name.lower()]
    # print(f"{user_id} for {name}")
    try:  
        # Get the attendance record for today
        # attendance_ref = db.collection('teacher_attendance').document(user_id).collection('last_recorded_date').document('record')
        attendance_ref = db.collection('teacher_attendance').document(user_id).collection('year').document('record')
        attendance_doc = attendance_ref.get()
        attendance_doc_dict = attendance_doc.to_dict()
        # DEBUG: 
        print(f"GOT attendence doc: {attendance_doc_dict}")

        if  not attendance_doc.exists:  
            attendance_ref.set(attendance_data)
            print(f"Attendence record SET for {name} for date: {today}")
        else:
            date_from_att_doc, month_att_count = get_date_and_count_from_attendance_data(attendance_doc_dict)    
            print(f"date form att doc: {date_from_att_doc}, today: {today}")
            if date_from_att_doc != today:    
                # Update attendance count if no record exists for today or if it's a new day)
                attendance_data = {
                    split_today[0]: {
                        split_today[1]: {
                            'count': month_att_count+1,
                            split_today[2]: {
                                'check_in_time': current_time
                            }
                        }
                    }
                }
                attendance_ref.update(attendance_data)
                print(f"Attendance recorded UPDATE for {name} for date:{today}")
            else:
                # Attendance record for today exists
                # this means that the person has already done attendence today. 
                print(f"{name}'s attendence has already been recorded for today.")
    except Exception as e:
        print("Error recording attendance:", e)


def get_teacher_ids():
    """
    outputs dict of teachers name(key) and id(value)
    """
    teachers_json_filename = 'teachers.json'
    teachers_dict = read_json_file(os.path.join(teachers_json_filename))
    return teachers_dict

