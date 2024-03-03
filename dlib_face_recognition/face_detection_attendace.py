from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
import face_recognition
import os
import time
import psutil

from utility.utility import *

# Global variables
FRAME_RATE = 5  # Desired frame rate (frames per second)
PREV_CAPTURE_TIME = 0
IMAGE = None
attendance_status_dict = {}
teacher_dict = {}
x1,x2,y1,y2 = None, None, None, None
classNames = []
encodeListKnown = []
db = None
name = None

# Function to set the event
def set_event(event):
    event.set()  # Set the event

# Function to process the image and extract face encodings
def process_face_encodings(match_found_event,successful_attendance_event, att_already_done_event,imgS, facesCurFrame):
    print(threading.current_thread().name)
    global encodeListKnown, classNames, name
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
    encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
    
    for encodeFace in encodesCurFrame:
        matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
        # print(faceDis)
        matchIndex = np.argmin(faceDis)

        if matches[matchIndex]:
            name = classNames[matchIndex].upper()
            print(f"{name} detected.")
            set_event(match_found_event)
            lower_name = name.lower()
            if(attendance_status_dict[teacher_dict[lower_name]]):
                print(f"Attendance for {name} is already done for today")
                set_event(att_already_done_event)
                return
            else: 
                # if attencende for today is not done, then only call backend api
                print(f"attendenca for {name} is not done today. Recording Attendane...")
                # make attendance: calling firebase in different thread
                if(markAttendance(name,db)==True):
                    set_event(successful_attendance_event)
                    return
        else:
            print(f"Thread {threading.current_thread().name}: Error: Failed to capture frame")

def process_image(face_detected_event):
    global attendance_status_dict, teacher_dict, x1,x2,y1,y2, encodeListKnown, classNames,db,name
    img = cv2.resize(IMAGE, (0, 0), None, 0.2, 0.2)
    imgS = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    facesCurFrame = face_recognition.face_locations(imgS)
    if(not facesCurFrame):
         return False, facesCurFrame, img
    else:
        for faceLoc in facesCurFrame:
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 5, x2 * 5, y2 * 5, x1 * 5
            set_event(face_detected_event)
        return True, facesCurFrame, img

def main():
    global attendance_status_dict, PREV_CAPTURE_TIME, FRAME_RATE, IMAGE, teacher_dict, classNames,db, encodeListKnown, name
    db = initialize_firestore()
    attendance_status_dict = get_attendance_dict_for_today(db)  
    teacher_dict = get_teachers_dict()
    attendace_status_today=switch_keys(attendance_status_dict, teacher_dict)
    print(f"Attendance Status for today: {attendace_status_today}")
    
    path = 'Training_images'
    images = []
    myList = os.listdir(path)
    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])

    encodeListKnown = findEncodings(images)
    print('Encoding Complete')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Thread {threading.current_thread().name}: Error: Failed to open camera")
        return
    
    face_detected_event = threading.Event()
    match_found_event = threading.Event()
    successful_attendance_event = threading.Event()
    att_already_done_event = threading.Event()

    with ThreadPoolExecutor(max_workers=1) as executor:
        while True:
            time_elapsed = time.time() - PREV_CAPTURE_TIME
            
            if time_elapsed > 1. / FRAME_RATE:
                PREV_CAPTURE_TIME = time.time()
                
                success, img = cap.read()
                if success:
                    IMAGE = img
                    has_faces, facesCurFrame, imgS= process_image(face_detected_event=face_detected_event)
                    if(has_faces):
                    #     process_face_encodings(match_found_event,
                    #                                 successful_attendance_event,
                    #                                 att_already_done_event,
                    #                                 imgS, 
                    #                                 facesCurFrame)
                        executor.submit(process_face_encodings,                                                 
                                                    match_found_event,
                                                    successful_attendance_event,
                                                    att_already_done_event,
                                                    imgS, 
                                                    facesCurFrame)
                
                if face_detected_event.is_set():
                        cv2.rectangle(IMAGE, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        face_detected_event.clear() 
                if match_found_event.is_set():
                    cv2.rectangle(IMAGE, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                    cv2.putText(IMAGE, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    height, width, _ = IMAGE.shape
                    lower_name = name.lower()
                    if att_already_done_event.is_set():
                        cv2.putText(IMAGE, "Attendance Already Recorded For Today", (height//2-200, (width//2)+150), cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 255, 0), 2)
                        att_already_done_event.clear()
                    elif successful_attendance_event.is_set():
                        attendance_status_dict[teacher_dict[lower_name]]=True
                        print(f"Attendence status updated: {switch_keys(attendance_status_dict, teacher_dict)}")
                        cv2.putText(IMAGE, "Attendance Sucessfull Recorded.", (height//2-200, (width//2)+150), cv2.FONT_HERSHEY_COMPLEX, 0.1, (0, 255, 0), 2)
                        successful_attendance_event.clear()
                    
                    match_found_event.clear()

                # print(f"memory usage: {psutil.Process().memory_info().rss}")
                cv2.imshow("webcam", IMAGE)
            # Check for 'q' key pressed to exit the loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()