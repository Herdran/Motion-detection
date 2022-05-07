from threading import Timer
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QMainWindow, QHBoxLayout, QPushButton, QSizePolicy, QGroupBox, QComboBox, QSlider
from PySide6.QtGui import QPixmap, QAction, QImage
from PySide6.QtCore import Signal, Slot, Qt, QThread
from time import sleep
from time import time as timer
import sys
import cv2


class VideoThread(QThread):
    change_pixmap_signal = Signal(QImage)

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.status = True
        self.mode = 0
        self.sensitivity = 20
        self.avg = None

    def set_mode(self, mode):
        self.mode = mode

    def set_sensitivity(self, val):
        self.sensitivity = val

    def stop(self):
        self.status = False
        self.wait()

    def run(self):
        
        fps = -1
        if len(sys.argv) == 3:
            video = cv2.VideoCapture(sys.argv[2]) 
            if(sys.argv[1] == '-f'):
                fps = video.get(cv2.CAP_PROP_FPS)
                fps /= 1000
        else:
            video = cv2.VideoCapture(0)
            
        
        while self.status:
            start = timer()
            ret, frame = video.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.avg is None:
                self.avg = gray.copy().astype("float")
                continue

            if self.mode != 0:
                cv2.accumulateWeighted(gray, self.avg, 0.05)

                diff_frame = cv2.absdiff(cv2.convertScaleAbs(self.avg), gray)

                if self.mode != 1:
                    thresh_frame = cv2.threshold(diff_frame, self.sensitivity, 255, cv2.THRESH_BINARY)[1]
                    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

                    if self.mode != 2:
                        cnts, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        for contour in cnts:
                            if cv2.contourArea(contour) < 10000:
                                continue

                            (x, y, w, h) = cv2.boundingRect(contour)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

            if self.mode == 0:
                color_frame = cv2.cvtColor(gray, cv2.COLOR_BGR2RGB)
            elif self.mode == 1:
                color_frame = cv2.cvtColor(diff_frame, cv2.COLOR_BGR2RGB)
            elif self.mode == 2:
                color_frame = cv2.cvtColor(thresh_frame, cv2.COLOR_BGR2RGB)
            elif self.mode == 3:
                color_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                continue

            # Creating and scaling QImage
            h, w, ch = color_frame.shape
            img = QImage(color_frame.data, w, h, ch * w, QImage.Format_RGB888)
            scaled_img = img.scaled(640, 480, Qt.KeepAspectRatio)
            self.change_pixmap_signal.emit(scaled_img)

            if(fps != -1):
                diff = timer() - start
                while  diff < fps:
                    diff = timer() - start                 

        video.release()


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.running = "start"

        self.setWindowTitle("Demo build")
        self.setGeometry(0, 0, 700, 500)

        self.menu = self.menuBar()
        self.menu_file = self.menu.addMenu("File")
        exit_ = QAction("Exit", self, triggered=qApp.quit)
        self.menu_file.addAction(exit_)

        self.label = QLabel(self)
        self.label.setFixedSize(640, 480)

        self.thread = VideoThread(self)
        self.thread.finished.connect(self.close)
        self.thread.change_pixmap_signal.connect(self.update_image)

        self.combobox = QComboBox()
        for mode in ["Gray Frame", "Difference Frame", "Threshold Frame", "Color Frame"]:
            self.combobox.addItem(mode)
        self.combobox.setCurrentIndex(3)

        modes_layout = QHBoxLayout()
        modes_layout.addWidget(QLabel("Modes"), 10)
        modes_layout.addWidget(self.combobox, 90)

        self.group_modes = QGroupBox("Display modes")
        self.group_modes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.group_modes.setLayout(modes_layout)

        buttons_layout = QHBoxLayout()
        self.button1 = QPushButton("Start")
        self.button2 = QPushButton("Pause/Kill")

        self.button1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.button2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        buttons_layout.addWidget(self.button1)
        buttons_layout.addWidget(self.button2)

        self.button1.setEnabled(True)
        self.button2.setEnabled(False)

        right_side_layout = QHBoxLayout()
        right_side_layout.addWidget(self.group_modes, 1)
        right_side_layout.addLayout(buttons_layout, 1)

        self.sensitivity_slider = QSlider()
        self.sensitivity_slider.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(50)
        self.sensitivity_slider.setValue(25)

        slider_layout = QVBoxLayout()
        # sensitivity range display is not centered
        slider_layout.addWidget(QLabel("50"), 10)
        slider_layout.addWidget(self.sensitivity_slider, 80)
        slider_layout.addWidget(QLabel("0"), 10)

        self.group_sensitivity = QGroupBox("Sensitivity")
        self.group_sensitivity.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.group_sensitivity.setLayout(slider_layout)

        frame_and_slider = QHBoxLayout()
        frame_and_slider.addWidget(self.label)
        frame_and_slider.addWidget(self.group_sensitivity)

        layout = QVBoxLayout()
        layout.addLayout(frame_and_slider)
        layout.addLayout(right_side_layout)

        widget = QWidget(self)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.button1.clicked.connect(self.start)
        self.button2.clicked.connect(self.pause_kill)
        self.combobox.currentIndexChanged.connect(self.set_mode)
        self.sensitivity_slider.sliderMoved.connect(self.set_sensitivity)
        
        

    @Slot(QImage)
    def update_image(self, cv_img):
        if self.running:
            self.label.setPixmap(QPixmap.fromImage(cv_img))

    @Slot()
    def start(self):
        if self.running == "start":
            self.thread.set_mode(self.combobox.currentIndex())
            self.thread.start()
            self.button1.setEnabled(False)
            self.button2.setEnabled(True)
            self.running = True
        elif not self.running:
            self.button1.setEnabled(False)
            self.button2.setEnabled(True)
            self.running = True

    @Slot()
    def set_mode(self, index):
        self.thread.set_mode(index)

    @Slot()
    def set_sensitivity(self, val):
        self.thread.set_sensitivity(val)

    @Slot()
    def pause_kill(self):
        if self.running:
            self.running = False
            self.button1.setEnabled(True)
        else:
            self.button2.setEnabled(False)
            self.button1.setEnabled(True)
            self.thread.stop()
            cv2.destroyAllWindows()
            self.thread.terminate()
            # This way of quitting gives a warning
            quit()


if __name__ == "__main__":
    if (len(sys.argv) not in [1, 3] or (len(sys.argv) == 3 and sys.argv[1] not in ['-f', '-s'])):
        print("To use: ");
        print(sys.argv[0], "- for running camera")
        print(sys.argv[0], "-f [path] - for running local video")
        print(sys.argv[0], "-s [link] - for running video from stream (eg. rtp)")
        exit(1)
        
    app = QApplication()
    a = App()
    a.show()
    sys.exit(app.exec())
