import copy
import face_recognition
import cv2
from datetime import datetime
import os
import json
import firebase_admin
from firebase_admin import firestore, credentials
import threading
# Global lock for synchronizing access to process_image function
attendance_lock = threading.Lock()

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
    count = attendence_doc[year][month]['count']
    day = list(attendence_doc[year][month].keys())
    day.remove('count')
    day.sort(reverse=True)
    day= day[0]

    # Construct the desired string
    date_string = f"{year}-{month}-{day}"
    return date_string, count


def markAttendance(name, db):
    print("markAttendance function called. ")
    with attendance_lock:
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"Thread {threading.current_thread().name}: ")
        """
        Record attendance in Firestore.
        """
        # Get today's date
        # TODO: need the data for time
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
        teacher_ids = get_teachers_dict()
        user_id = teacher_ids[name.lower()]
        try:  
            # Get the attendance record for today
            # attendance_ref = db.collection('teacher_attendance').document(user_id).collection('last_recorded_date').document('record')
            attendance_ref = db.collection('teacher_attendance').document(user_id).collection('year').document('record')
            attendance_doc = attendance_ref.get()
            attendance_doc_dict = attendance_doc.to_dict()
            temp_dict = copy.deepcopy(attendance_doc_dict)
            # DEBUG: 
            print(f"GOT attendence doc: {attendance_doc_dict}")

            if attendance_doc.exists:  
                date_from_att_doc, month_att_count = get_date_and_count_from_attendance_data(attendance_doc_dict) 
                date_from_att_doc_split = date_from_att_doc.split("-")   
                print(f"date form att doc: {date_from_att_doc}, today: {today}")
                # also the date_from_att_doc should be in correct format.
                if (all_elements_convertible_to_int(split_today) and date_from_att_doc != today):
                    # year not equal
                    if (date_from_att_doc_split[0] != split_today[0]):
                        print("year not equal")
                        attendance_ref.update(attendance_data)
                        return True
                    #month no equal 
                    if (date_from_att_doc_split[1] != split_today[1]):
                        print("month not equal")
                        temp = attendance_data[split_today[0]]
                        # print(f"before temp: {temp}")
                        temp_dict[split_today[0]][split_today[1]] = temp[split_today[1]]
                        # print(f"last:: {temp_dict}")
                        attendance_ref.update(temp_dict)
                        return True
                    #day not equal
                    if(date_from_att_doc_split[2]!=split_today[2]):
                        # print(temp_dict)
                        temp = attendance_data[split_today[0]][split_today[1]]
                        del temp['count']
                        temp_dict[split_today[0]][split_today[1]][split_today[2]] = temp[split_today[2]]
                        temp_dict[split_today[0]][split_today[1]]['count'] = month_att_count + 1
                        print(f"temp_dict: {temp_dict}")
                        attendance_ref.update(temp_dict)
                        print(f"Attendance recorded UPDATE for {name} for date:{today}")
                        return True
                else:
                    return False
            else:
                # Attendance record document does not exist.
                attendance_ref.set(attendance_data)
                print(f"Attendence record SET for {name} for date: {today}")
                return True
        except Exception as e:
            print("Error recording attendance:", e)
            return False

def get_teachers_dict():
    """
    outputs dict of teachers name(key) and id(value)
    """
    teachers_json_filename = 'teachers.json'
    teachers_dict = read_json_file(os.path.join(teachers_json_filename))
    return teachers_dict

def get_attendance_dict_for_today(db):
    attendance_ref = db.collection('teacher_attendance')
    teacher_id_dict = get_teachers_dict()
    today = datetime.now().strftime("%Y-%m-%d")
    # split_today = today.split(sep="-")

    attendance_status_dict = {}
    for i,teacher_id in enumerate(teacher_id_dict.values()):
        attendance_doc = attendance_ref.document(teacher_id).collection('year').document('record').get()
        attendance_doc_dict = attendance_doc.to_dict()
        # print(attendance_doc_dict)
        date, _ = get_date_and_count_from_attendance_data(attendence_doc=attendance_doc_dict)
        if(date == today ):
            attendance_status_dict[teacher_id] = True
        else:
            attendance_status_dict[teacher_id] = False
    return attendance_status_dict

def switch_keys(dict1, dict2):

    # Create a new dictionary to store the attendance status with teacher names as keys
    dict3 = {}

    # Iterate through the attendance status dictionary
    for teacher_name, teacher_key in dict2.items():
        # Use the teacher key to get the attendance status
        temp = dict1.get(teacher_key)
        # Add the attendance status to the new dictionary with teacher name as key
        dict3[teacher_name] = temp

    return dict3

def are_all_numbers(lst):
    for element in lst:
        if not isinstance(element, (int, float)):
            return False
    return True

def all_elements_convertible_to_int(lst):
    return all(isinstance(elem, int) or (isinstance(elem, str) and elem.isdigit()) for elem in lst)