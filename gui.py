import cv2
import time
import sys
import os
import ctypes
import customtkinter as ctk
from PIL import Image, ImageTk

from posture_engine import PrecisionPostureMonitor

# دالة التعامل مع مسارات الملفات أثناء التجميع بـ PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
myappid = 'spineshield.ai.posture.monitor'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class PostureApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SpineShield AI")
        self.iconbitmap(resource_path("icon.ico"))
        
        app_width = 1080
        app_height = 640
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - app_width) // 2
        y = (screen_height - app_height) // 2

        self.geometry(f"{app_width}x{app_height}+{x}+{y}")
        self.resizable(False, False)

        self.monitor = PrecisionPostureMonitor(resource_path('pose_landmarker.task'))
        self.cap = cv2.VideoCapture(0)

        self.create_widgets()

        self.update_frame()
        self.is_muted = False

    def create_widgets(self):
        self.video_frame = ctk.CTkFrame(self, width=650, height=580, corner_radius=18, fg_color="#18181A")
        self.video_frame.pack(side="left", padx=(20, 10), pady=20, fill="both", expand=True)

        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(fill="both", expand=True, padx=12, pady=12)

        self.sidebar = ctk.CTkFrame(self, width=360, height=580, corner_radius=18, fg_color="#1E1E24")
        self.sidebar.pack(side="right", padx=(10, 20), pady=20, fill="y")
        self.sidebar.pack_propagate(False)

        self.header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.header_frame.pack(padx=20, pady=(15, 5), fill="x")

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="SpineShield AI", 
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.pack(side="left")

        self.mute_btn = ctk.CTkButton(
            self.header_frame,
            text="🔊",
            width=38,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=18),
            fg_color="#2A2A32",
            hover_color="#3A3A42",
            command=self.toggle_mute
        )
        self.mute_btn.pack(side="right")

        self.status_card = ctk.CTkFrame(self.sidebar, fg_color="#2A2A32", corner_radius=14, height=85)
        self.status_card.pack(padx=20, pady=5, fill="x")
        self.status_card.pack_propagate(False)

        self.status_main = ctk.CTkLabel(
            self.status_card, 
            text="NOT CALIBRATED", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#8E8E93"
        )
        self.status_main.pack(padx=10, pady=(12, 2))

        self.status_reason = ctk.CTkLabel(
            self.status_card, 
            text="Sit straight & calibrate", 
            font=ctk.CTkFont(size=11, weight="normal"),
            text_color="#AAAAAA"
        )
        self.status_reason.pack(padx=10, pady=(0, 10))

        self.info_card = ctk.CTkFrame(self.sidebar, fg_color="#24242C", corner_radius=12)
        self.info_card.pack(padx=20, pady=5, fill="x")

        info_title = ctk.CTkLabel(
            self.info_card, 
            text="💡 Quick Instructions", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color="#00D4FF"
        )
        info_title.pack(anchor="w", padx=12, pady=(8, 2))

        instructions_text = (
            "1. Sit straight, pull shoulders back & look ahead.\n"
            "2. Press 'C' or click Calibrate to set posture.\n"
            "3. If changing seating position, sit straight & press 'C' again."
        )
        info_body = ctk.CTkLabel(
            self.info_card, 
            text=instructions_text, 
            font=ctk.CTkFont(size=10), 
            text_color="#CCCCCC", 
            justify="left",
            wraplength=300
        )
        info_body.pack(anchor="w", padx=12, pady=(0, 2))

        info_alert = ctk.CTkLabel(
            self.info_card, 
            text="4. False alarm while sitting straight? Re-press 'C' to fix.", 
            font=ctk.CTkFont(size=10, weight="bold"), 
            text_color="#FF453A", 
            justify="left",
            wraplength=300
        )
        info_alert.pack(anchor="w", padx=12, pady=(0, 8))

        self.metrics_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.metrics_frame.pack(padx=20, pady=2, fill="x")

        self.trap_label = self.create_metric_row("Shoulder Position", "0%")
        self.area_label = self.create_metric_row("Posture Area", "0%")
        self.neck_label = self.create_metric_row("Neck Level", "0%")

        ctk.CTkLabel(self.sidebar, text="").pack(expand=True)

        self.calib_btn = ctk.CTkButton(
            self.sidebar, 
            text="Calibrate Sit (Press C)", 
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46,
            corner_radius=12,
            fg_color="#0066CC",
            hover_color="#0052A3",
            command=self.trigger_calibration
        )
        self.calib_btn.pack(padx=20, pady=(0, 4), fill="x")

        self.arrow_label = ctk.CTkLabel(
            self.sidebar, 
            text="👆 Press 'C' or click button above to calibrate 👆", 
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#FF9500"
        )
        self.arrow_label.pack(padx=20, pady=(0, 15))

        self.bind("<c>", lambda event: self.trigger_calibration())
        self.bind("<C>", lambda event: self.trigger_calibration())

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.monitor.is_muted = self.is_muted  
        if self.is_muted:
            self.mute_btn.configure(text="🔇", fg_color="#3A1C1C", hover_color="#5C2424")
        else:
            self.mute_btn.configure(text="🔊", fg_color="#2A2A32", hover_color="#3A3A42")

    def create_metric_row(self, title, default_val):
        row = ctk.CTkFrame(self.metrics_frame, fg_color="#26262E", corner_radius=10)
        row.pack(fill="x", pady=2)

        lbl_title = ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=11), text_color="#D1D1D6")
        lbl_title.pack(side="left", padx=10, pady=4)

        lbl_val = ctk.CTkLabel(row, text=default_val, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFFFFF")
        lbl_val.pack(side="right", padx=10, pady=4)

        return lbl_val

    def trigger_calibration(self):
        if hasattr(self, 'current_metrics'):
            self.monitor.calibrate(self.current_metrics)
            
            self.arrow_label.configure(text="✅ Baseline Locked Successfully", text_color="#30D158")
            self.status_card.configure(fg_color="#1C3829")
            self.status_main.configure(text="GOOD POSTURE", text_color="#30D158")
            self.status_reason.configure(text="Optimal posture active", text_color="#A3E5B0")

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            processed_frame, metrics = self.monitor.process(frame)
            self.current_metrics = metrics

            if self.monitor.calibrated and metrics[0] > 0:
                trap_score = int((metrics[0] / self.monitor.base_trap_ratio) * 100)
                area_score = int((metrics[2] / self.monitor.base_area_ratio) * 100)
                neck_score = int((metrics[1] / self.monitor.base_neck_ratio) * 100)

                self.trap_label.configure(text=f"{trap_score}%")
                self.area_label.configure(text=f"{area_score}%")
                self.neck_label.configure(text=f"{neck_score}%")

                issues = []
                if trap_score < 96 or area_score < 94:
                    issues.append("Shoulders Forward")
                if neck_score < 88:
                    issues.append("Neck Down")

                if issues:
                    self.status_card.configure(fg_color="#3A1C1C")
                    self.status_main.configure(text="BAD POSTURE", text_color="#FF453A")
                    self.status_reason.configure(text=", ".join(issues), text_color="#FF9F9A")
                else:
                    self.status_card.configure(fg_color="#1C3829")
                    self.status_main.configure(text="GOOD POSTURE", text_color="#30D158")
                    self.status_reason.configure(text="Optimal posture maintained", text_color="#A3E5B0")

            cv2_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_image)
            imgtk = ctk.CTkImage(light_image=img, dark_image=img, size=(630, 470))

            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.after(10, self.update_frame)

    def close_app(self):
        self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = PostureApp()
    app.protocol("WM_DELETE_WINDOW", app.close_app)
    app.mainloop()