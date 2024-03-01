import cv2
import numpy as np
import face_recognition
import os
import time

from utility.utility import *

# Global variables
FRAME_RATE = 10  # Desired frame rate (frames per second)
PREV_CAPTURE_TIME = 0
IMAGE = None
# Global lock for synchronizing access to process_image function
process_image_lock = threading.Lock()
attendance_status_dict = {}

def process_image(encodeListKnown, classNames,db):
    global attendance_status_dict
    with process_image_lock:
    # print(f"Thread {threading.current_thread().name}: captured at time: {prev_capture_time}")
        imgS = cv2.resize(IMAGE, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

        facesCurFrame = face_recognition.face_locations(imgS)
        if (facesCurFrame):
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                # print(faceDis)
                matchIndex = np.argmin(faceDis)

                if matches[matchIndex]:
                    name = classNames[matchIndex].upper()
                    print(f"{name} detected.")
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(IMAGE, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.rectangle(IMAGE, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                    cv2.putText(IMAGE, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    teacher_dict = get_teachers_dict()
                    print(f"attendance_status_dict: {attendance_status_dict}")
                    print(f"teacher_dict: {teacher_dict}")
                    print(f"teacher_dict[name.lower()] : {teacher_dict[name.lower()]}")
                    print(f"\n attendance_status_dict[teacher_dict[name.lower()]]: {attendance_status_dict[teacher_dict[name.lower()]]}")
                    if(attendance_status_dict[teacher_dict[name.lower()]]==False):
                        # if attencende for today is not done, then only call backend api
                        print(f"attendenca for {name} is not done today. Recording Attendane...")
                        # make attendance: calling firebase in different thread
                        if(markAttendance(name,db)==True):
                            attendance_status_dict[teacher_dict[name.lower()]]=True
                            print(f"Attendence status updated: {switch_keys(attendance_status_dict, teacher_dict)}")
                    else: 
                        print(f"Attendance for {name} is already done for today")
                        height, width, _ = IMAGE.shape
                        cv2.putText(IMAGE, "Attendance already done.", (height//2-100, (width//2)+50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow("webcam", IMAGE)
                        cv2.waitKey(1)
                else:
                    print(f"Thread {threading.current_thread().name}: Error: Failed to capture frame")

def main():
    global attendance_status_dict
    db = initialize_firestore()
    attendance_status_dict = get_attendance_dict_for_today(db)  
    teacher_dict = get_teachers_dict()
    attendence_status_today=switch_keys(attendance_status_dict, teacher_dict)
    print(f"Attendance Status for today: {attendence_status_today}")
    
    path = 'Training_images'
    images = []
    classNames = []
    myList = os.listdir(path)
    print(myList)
    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])
    print(classNames)

    encodeListKnown = findEncodings(images)
    print('Encoding Complete')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"Thread {threading.current_thread().name}: Error: Failed to open camera")
        return
    
    global PREV_CAPTURE_TIME, FRAME_RATE, IMAGE

    while True:
        time_elapsed = time.time() - PREV_CAPTURE_TIME
        
        if time_elapsed > 1. / FRAME_RATE:
            PREV_CAPTURE_TIME = time.time()
            
            success, img = cap.read()
            if success:
                IMAGE = img
                process_image(encodeListKnown=encodeListKnown, 
                              classNames=classNames, 
                              db=db)
            cv2.imshow("webcam", IMAGE)
        # Check for 'q' key pressed to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    main()