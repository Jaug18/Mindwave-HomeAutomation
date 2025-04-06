#coding: latin-1

# Use me to record a video with an timestamped overlay.
# You can later check the video and see what happened with they guy under study.

import cv2

import time, datetime

cap = cv2.VideoCapture(0)
cap.set(3,640)
cap.set(4,480)

w = cap.get(cv2.CAP_PROP_FRAME_WIDTH);
h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT);
fourcc = cv2.VideoWriter_fourcc(*"MJPG")
out = cv2.VideoWriter('./data/output.avi',fourcc, 24.0, (int(w),int(h)))

while (True):
    ret, frame = cap.read()

    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d-%H-%M-%S.%f')
    #cv2.rectangle(frame, (420, 205), (595, 385),(0, 0, 255), -1)
    cv2.putText(frame, "T={}".format(st), (10, 30), cv2.FONT_ITALIC , 1.0, (0, 0, 255), 3)

    out.write(frame)
    cv2.imshow('Video Stream', frame)

    key = cv2.waitKey(1) & 0xFF

    # if the `q` key was pressed, break from the loop
    if key == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
