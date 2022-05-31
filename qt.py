from threading import Timer
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QMainWindow, QHBoxLayout, QPushButton, QSizePolicy, QGroupBox, QComboBox, QSlider
from PySide6.QtGui import QPixmap, QAction, QImage
from PySide6.QtCore import Signal, Slot, Qt, QThread
from superqt import QRangeSlider
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
        self.detection_sensitivity = 20
        self.avg = None
        self.x_min = 0
        self.x_max = 640
        self.y_min = 0
        self.y_max = 480
        self.min_contour_size = 150

    def set_mode(self, mode):
        self.mode = mode

    def set_size(self, size):
        self.min_contour_size = size

    def set_detection_sensitivity(self, val):
        self.detection_sensitivity = val

    def set_senstivity_range_h(self, val):
        self.x_min = int(val[0])
        self.x_max = int(val[1])

    def set_senstivity_range_v(self, val):
        self.y_min = int(val[0])
        self.y_max = int(val[1])

    def stop(self):
        self.status = False
        self.wait()

    def run(self):

        fps = -1
        if len(sys.argv) == 3:
            video = cv2.VideoCapture(sys.argv[2])
            if sys.argv[1] == '-f':
                fps = video.get(cv2.CAP_PROP_FPS)
                fps /= 1000
        else:
            video = cv2.VideoCapture(0)

        while self.status:
            start = timer()
            ret, frame = video.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (640, 480))

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.avg is None:
                self.avg = gray.copy().astype("float")
                continue

            if self.mode != 0:
                cv2.accumulateWeighted(gray, self.avg, 0.05)

                diff_frame = cv2.absdiff(cv2.convertScaleAbs(self.avg), gray)

                if self.mode != 1:
                    thresh_frame = cv2.threshold(diff_frame, self.detection_sensitivity, 255, cv2.THRESH_BINARY)[1]
                    thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

                    if self.mode != 2:
                        cnts, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                        for contour in cnts:
                            (x, y, w, h) = cv2.boundingRect(contour)

                            if self.x_min <= x and x + w <= self.x_max and \
                                    self.y_min <= y and y + h <= self.y_max and \
                                    cv2.contourArea(contour) >= self.min_contour_size:


                            # if x + w <= self.x_min or x >= self.x_max or y + h <= self.y_min or y >= self.y_max:
                            #     continue
                            #
                            # w = w - max(self.x_min - x, 0) - max((x + w) - self.x_max, 0)
                            # x = max(x, self.x_min)
                            #
                            # h = h - max(self.y_min - y, 0) - max((y + h) - self.y_max, 0)
                            # y = max(y, self.y_min)
                            #
                            # if w * h < self.min_contour_size:
                            #     continue


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

            if (fps != -1):
                diff = timer() - start
                while diff < fps:
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
        modes_layout.addWidget(self.combobox, 90)

        self.group_modes = QGroupBox("Display modes")
        self.group_modes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.group_modes.setLayout(modes_layout)

        self.combobox2 = QComboBox()
        for mode in ["150", "500", "1000", "10000"]:
            self.combobox2.addItem(mode)
        self.combobox2.setCurrentIndex(0)

        sizes_layout = QHBoxLayout()
        sizes_layout.addWidget(self.combobox2, 90)

        self.group_sizes = QGroupBox("Minimal contour size")
        self.group_sizes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.group_sizes.setLayout(sizes_layout)


        buttons_layout = QHBoxLayout()
        self.button1 = QPushButton("Start")
        self.button2 = QPushButton("Pause/Kill")

        self.button1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.button2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        buttons_layout.addWidget(self.button1)
        buttons_layout.addWidget(self.button2)

        self.button1.setEnabled(True)
        self.button2.setEnabled(False)

        bottom_side_layout = QHBoxLayout()
        bottom_side_layout.addWidget(self.group_modes, 5)
        bottom_side_layout.addWidget(self.group_sizes, 1)
        bottom_side_layout.addLayout(buttons_layout, 5)

        self.detection_sensitivity_slider = QSlider()
        self.detection_sensitivity_slider.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.detection_sensitivity_slider.setMinimum(0)
        self.detection_sensitivity_slider.setMaximum(50)
        self.detection_sensitivity_slider.setValue(25)

        slider_layout = QVBoxLayout()
        # sensitivity range display is not centered
        slider_layout.addWidget(QLabel("50"), 10)
        slider_layout.addWidget(self.detection_sensitivity_slider, 80)
        slider_layout.addWidget(QLabel("0"), 10)

        self.group_sensitivity = QGroupBox("Sensitivity")
        self.group_sensitivity.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.group_sensitivity.setLayout(slider_layout)

        self.sensitivity_range_slider_v = QRangeSlider()
        self.sensitivity_range_slider_v.setInvertedAppearance(True)
        self.sensitivity_range_slider_h = QRangeSlider()
        self.sensitivity_range_slider_h.setOrientation(Qt.Horizontal)

        self.sensitivity_range_slider_v.setMinimum(0)
        self.sensitivity_range_slider_h.setMinimum(0)

        self.sensitivity_range_slider_v.setMaximum(480)
        self.sensitivity_range_slider_h.setMaximum(640)

        self.sensitivity_range_slider_v.setValue([0, 480])
        self.sensitivity_range_slider_h.setValue([0, 640])

        self.frame_and_slider_h = QHBoxLayout()
        self.frame_and_slider_h.addWidget(self.label)
        self.frame_and_slider_h.addWidget(self.sensitivity_range_slider_v)

        self.frame_and_slider_v = QHBoxLayout()
        self.frame_and_slider_v.addWidget(self.sensitivity_range_slider_h)
        self.frame_and_slider_v.addSpacing(20)

        self.frame_and_sliders = QVBoxLayout()
        self.frame_and_sliders.addLayout(self.frame_and_slider_h)
        self.frame_and_sliders.addLayout(self.frame_and_slider_v)

        frame_sliders_sensitivity = QHBoxLayout()
        frame_sliders_sensitivity.addLayout(self.frame_and_sliders)
        frame_sliders_sensitivity.addWidget(self.group_sensitivity)

        main_layout = QVBoxLayout()
        main_layout.addLayout(frame_sliders_sensitivity)
        main_layout.addLayout(bottom_side_layout)

        widget = QWidget(self)
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

        self.button1.clicked.connect(self.start)
        self.button2.clicked.connect(self.pause_kill)
        self.combobox.currentIndexChanged.connect(self.set_mode)
        self.combobox2.currentTextChanged.connect(self.set_size)
        self.detection_sensitivity_slider.sliderMoved.connect(self.set_detection_sensitivity)
        self.sensitivity_range_slider_v.sliderMoved.connect(self.set_senstivity_range_v)
        self.sensitivity_range_slider_h.sliderMoved.connect(self.set_senstivity_range_h)

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
    def set_size(self, text):
        self.thread.set_size(int(text))

    @Slot()
    def set_detection_sensitivity(self, val):
        self.thread.set_detection_sensitivity(val)

    @Slot()
    def set_senstivity_range_h(self, val):
        self.thread.set_senstivity_range_h(val)

    @Slot()
    def set_senstivity_range_v(self, val):
        self.thread.set_senstivity_range_v(val)

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
    if len(sys.argv) not in [1, 3] or (len(sys.argv) == 3 and sys.argv[1] not in ['-f', '-s']):
        print("To use: ")
        print(sys.argv[0], "- for running camera")
        print(sys.argv[0], "-f [path] - for running local video")
        print(sys.argv[0], "-s [link] - for running video from stream (eg. rtp)")
        exit(1)

    app = QApplication()
    a = App()
    a.show()
    sys.exit(app.exec())
