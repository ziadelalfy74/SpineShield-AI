import cv2
import math
import time
import winsound
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class PrecisionPostureMonitor:
    def __init__(self, model_path='pose_landmarker.task'):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

        self.calibrated = False
        self.is_muted = False  
        
        self.base_trap_ratio = 0.0
        self.base_neck_ratio = 0.0
        self.base_area_ratio = 0.0  
        
        self.bad_posture_start = None
        self.last_beep_time = 0

        self.smoothed_trap_ratio = None
        self.smoothed_neck_ratio = None
        self.smoothed_area_ratio = None
        self.alpha = 0.25

    def process(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        results = self.detector.detect(mp_image)
        status = "Sit straight"
        color = (128, 128, 128)
        issues = []
        details_text = "Press 'C' to Calibrate"

        metrics = (0.0, 0.0, 0.0)

        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            lm = results.pose_landmarks[0]

            pts = {}
            for idx in [0, 7, 8, 11, 12]:
                pts[idx] = (int(lm[idx].x * w), int(lm[idx].y * h))

            nose = pts[0]
            l_ear, r_ear = pts[7], pts[8]
            l_shoulder, r_shoulder = pts[11], pts[12]
            
            chest_center = ((l_shoulder[0] + r_shoulder[0]) // 2, (l_shoulder[1] + r_shoulder[1]) // 2)

            ear_width = math.dist(l_ear, r_ear) + 1e-6

            l_trap_dist = math.dist(l_ear, l_shoulder)
            r_trap_dist = math.dist(r_ear, r_shoulder)
            avg_trap_dist = (l_trap_dist + r_trap_dist) / 2.0
            raw_trap_ratio = avg_trap_dist / ear_width

            raw_neck_dist = math.dist(nose, chest_center)
            raw_neck_ratio = raw_neck_dist / ear_width

            sh_width = math.dist(l_shoulder, r_shoulder)
            trap_height = abs(((l_shoulder[1] + r_shoulder[1]) / 2.0) - ((l_ear[1] + r_ear[1]) / 2.0))
            raw_area_ratio = ((ear_width + sh_width) * trap_height / 2.0) / (ear_width ** 2)

            if self.smoothed_trap_ratio is None:
                self.smoothed_trap_ratio = raw_trap_ratio
                self.smoothed_neck_ratio = raw_neck_ratio
                self.smoothed_area_ratio = raw_area_ratio
            else:
                self.smoothed_trap_ratio = (self.alpha * raw_trap_ratio) + ((1 - self.alpha) * self.smoothed_trap_ratio)
                self.smoothed_neck_ratio = (self.alpha * raw_neck_ratio) + ((1 - self.alpha) * self.smoothed_neck_ratio)
                self.smoothed_area_ratio = (self.alpha * raw_area_ratio) + ((1 - self.alpha) * self.smoothed_area_ratio)

            curr_trap_ratio = self.smoothed_trap_ratio
            curr_neck_ratio = self.smoothed_neck_ratio
            curr_area_ratio = self.smoothed_area_ratio
            
            metrics = (curr_trap_ratio, curr_neck_ratio, curr_area_ratio)

            if self.calibrated:
                trap_score = curr_trap_ratio / self.base_trap_ratio
                neck_score = curr_neck_ratio / self.base_neck_ratio
                area_score = curr_area_ratio / self.base_area_ratio


                if neck_score < 0.83:
                    issues.append("Neck Down")

                if trap_score < 0.96 or area_score < 0.94:
                    issues.append("Shoulders Forward")

                if issues:
                    status = f"BAD: {', '.join(issues)}"
                    color = (0, 0, 255)

                    if self.bad_posture_start is None:
                        self.bad_posture_start = time.time()
                    elif time.time() - self.bad_posture_start > 1.5:
                        if not self.is_muted and (time.time() - self.last_beep_time > 1.2):
                            winsound.Beep(1800, 150)
                            winsound.Beep(1200, 150)
                            self.last_beep_time = time.time()
                else:
                    status = "Good Posture"
                    color = (0, 255, 0)
                    self.bad_posture_start = None

                details_text = f"Trap:{int(trap_score*100)}% | Area:{int(area_score*100)}% | Neck:{int(neck_score*100)}%"
            else:
                details_text = "Sit Straight & Press 'C' to Calibrate"

            cv2.line(frame, l_ear, r_ear, (255, 255, 0), 2)
            cv2.line(frame, l_ear, l_shoulder, (0, 255, 255), 2)
            cv2.line(frame, r_ear, r_shoulder, (0, 255, 255), 2)
            cv2.line(frame, nose, chest_center, (255, 100, 255), 2)
            cv2.line(frame, l_shoulder, r_shoulder, color, 3)

            cv2.circle(frame, nose, 5, (0, 255, 255), -1)
            cv2.circle(frame, chest_center, 5, (255, 255, 0), -1)

        cv2.rectangle(frame, (10, 10), (520, 90), (0, 0, 0), -1)
        cv2.putText(frame, status, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        cv2.putText(frame, details_text, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)

        return frame, metrics

    def calibrate(self, metrics):
        if metrics[0] > 0 and metrics[1] > 0 and metrics[2] > 0:
            self.base_trap_ratio, self.base_neck_ratio, self.base_area_ratio = metrics
            self.calibrated = True

def main():
    monitor = PrecisionPostureMonitor('pose_landmarker.task')
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame, metrics = monitor.process(frame)
        cv2.imshow('Ultimate Posture Monitor', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('c') or key == ord('C'):
            monitor.calibrate(metrics)
            print("[CALIBRATED] Posture Baseline Locked!")
        elif key == ord('q') or key == ord('Q'):
            break

    cap.release()
    cv2.destroyAllWindows()

#if __name__ == "__main__":
 #   main()