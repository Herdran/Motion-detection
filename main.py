import cv2

avg = None

video = cv2.VideoCapture(0)

mode_switch = 0
sensitivity = 20

while True:
    ret, frame = video.read()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if avg is None:
        avg = gray.copy().astype("float")
        continue

    cv2.accumulateWeighted(gray, avg, 0.05)

    diff_frame = cv2.absdiff(cv2.convertScaleAbs(avg), gray)

    thresh_frame = cv2.threshold(diff_frame, sensitivity, 255, cv2.THRESH_BINARY)[1]
    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

    cnts, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in cnts:
        if cv2.contourArea(contour) < 10000:
            continue

        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

    # cv2.imshow("Gray Frame", gray)
    # cv2.imshow("Difference Frame", diff_frame)
    # cv2.imshow("Threshold Frame", thresh_frame)
    # cv2.imshow("Color Frame", frame)

    if mode_switch == 0:
        cv2.imshow("Frame", gray)
    elif mode_switch == 1:
        cv2.imshow("Frame", diff_frame)
    elif mode_switch == 2:
        cv2.imshow("Frame", thresh_frame)
    elif mode_switch == 3:
        cv2.imshow("Frame", frame)

    key = cv2.waitKey(1)

    if key & 0xFF == ord('q'):
        break
    elif key & 0xFF == ord('d'):
        mode_switch = (mode_switch + 1) % 4

video.release()
cv2.destroyAllWindows()
