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
    # print("get_date_and_count_form_attendence_data() called.")
    # Extract the keys
    year = list(attendence_doc.keys())[0]
    month = list(attendence_doc[year].keys())[0]
    count = attendence_doc[year][month]['count']
    day = list(attendence_doc[year][month].keys())
    day.remove('count')
    day.sort(reverse=True)
    print(f" inside get_date_and_count_from_attendence=> day_list_reverse: {day}")
    day= day[0]

    # Construct the desired string
    date_string = f"{year}-{month}-{day}"
    print(f"get_date_and_count_from_attendance_data: {date_string}")
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
        # print(f"{user_id} for {name}")
        try:  
            # Get the attendance record for today
            # attendance_ref = db.collection('teacher_attendance').document(user_id).collection('last_recorded_date').document('record')
            attendance_ref = db.collection('teacher_attendance').document(user_id).collection('year').document('record')
            attendance_doc = attendance_ref.get()
            attendance_doc_dict = attendance_doc.to_dict()
            temp_dict = copy.deepcopy(attendance_doc_dict)
            # DEBUG: 
            print(f"GOT attendence doc: {attendance_doc_dict}")

            if  not attendance_doc.exists:  
                attendance_ref.set(attendance_data)
                print(f"Attendence record SET for {name} for date: {today}")
            else:
                date_from_att_doc, month_att_count = get_date_and_count_from_attendance_data(attendance_doc_dict)    
                print(f"date form att doc: {date_from_att_doc}, today: {today}")
                # also the date_from_att_doc should be in correct format.
                print(f"are_all_numbers: are_all_numbers(split_today)")
                if (all_elements_convertible_to_int(split_today) and date_from_att_doc != today):
                    attendance_data = attendance_doc_dict[split_today[0]][split_today[1]]
                    attendance_data.update({'count': month_att_count+1, split_today[2]: {'check_in_time': "current_time"}})
                    month_attendance_data = attendance_doc_dict[split_today[0]]
                    month_attendance_data.update({split_today[1]: attendance_data})
                    temp_dict[split_today[0]] = month_attendance_data
                    print(temp_dict)
                    attendance_ref.update(temp_dict)
                    print(f"Attendance recorded UPDATE for {name} for date:{today}")
                else:
                    # Attendance record for today exists
                    # this means that the person has already done attendence today. 
                    print(f"Either last attended date = Today OR date could not be retrieved .")
        except Exception as e:
            print("Error recording attendance:", e)
            return False
    return True

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
    split_today = today.split(sep="-")

    attendance_status_dict = {}
    for i,teacher_id in enumerate(teacher_id_dict.values()):
        attendance_doc = attendance_ref.document(teacher_id).collection('year').document('record').get()
        attendance_doc_dict = attendance_doc.to_dict()
        print(f"{teacher_id}: docs = {attendance_doc_dict}")
        date, count = get_date_and_count_from_attendance_data(attendence_doc=attendance_doc_dict)
        # temp_dict = copy.deepcopy(attendance_doc_dict)
        # attendance_data = attendance_doc_dict[split_today[0]][split_today[1]]
        # attendance_data.update({'count': count+1, split_today[2]: {'check_in_time': "current_time"}})
        # month_attendance_data = attendance_doc_dict[split_today[0]]
        # month_attendance_data.update({split_today[1]: attendance_data})
        # temp_dict[split_today[0]] = month_attendance_data
        # print(f"temp_dict: {temp_dict}")
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