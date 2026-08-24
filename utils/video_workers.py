import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class FrameExtractorWorker(QThread):
    # Emit frame index and the corresponding thumbnail image
    frame_extracted = pyqtSignal(int, QImage)
    extraction_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, video_path, target_height=150):
        super().__init__()
        self.video_path = video_path
        self.target_height = target_height
        self._is_running = True

    def run(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error_occurred.emit("Video dosyası açılamadı.")
                return

            frame_idx = 0
            while self._is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sadece belli aralıklarla frame almak performans için daha iyi olabilir
                # Ancak kullanıcı tüm frameleri istediği içinepsini işliyoruz.
                
                # OpenCV uses BGR, Qt uses RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize for thumbnail keeping aspect ratio to save memory
                orig_h, orig_w = rgb_frame.shape[:2]
                scale = self.target_height / float(orig_h)
                new_width = int(orig_w * scale)
                thumb = cv2.resize(rgb_frame, (new_width, self.target_height))
                
                h, w, ch = thumb.shape
                bytes_per_line = ch * w
                q_img = QImage(thumb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                
                self.frame_extracted.emit(frame_idx, q_img)
                frame_idx += 1
                
                # Yield thread briefly to prevent UI freezing if there are many frames
                self.msleep(1)

            cap.release()
            self.extraction_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False

class VideoExporterWorker(QThread):
    progress_updated = pyqtSignal(int)
    export_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, source_video, target_video, start_frame, end_frame, fps):
        super().__init__()
        self.source_video = source_video
        self.target_video = target_video
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.fps = fps
        self._is_running = True

    def run(self):
        try:
            cap = cv2.VideoCapture(self.source_video)
            if not cap.isOpened():
                self.error_occurred.emit("Kaynak video açılamadı.")
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.target_video, fourcc, self.fps, (width, height))
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            
            total_frames = self.end_frame - self.start_frame + 1
            processed = 0

            while self._is_running and processed < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                out.write(frame)
                processed += 1
                
                # Sadece belli aralıklarla % gönder (UI'ı çok meşgul etmemek için)
                if processed % 5 == 0 or processed == total_frames:
                    progress = int((processed / total_frames) * 100)
                    self.progress_updated.emit(progress)
            
            cap.release()
            out.release()
            
            if self._is_running:
                self.export_finished.emit()
                
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False

from utils.image_processing import inpaint_region

class BatchInpaintWorker(QThread):
    progress_updated = pyqtSignal(int)
    inpaint_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, source_video, target_video, start_frame, end_frame, roi_rect, fps):
        super().__init__()
        self.source_video = source_video
        self.target_video = target_video
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.roi_rect = roi_rect
        self.fps = fps
        self._is_running = True

    def run(self):
        try:
            cap = cv2.VideoCapture(self.source_video)
            if not cap.isOpened():
                self.error_occurred.emit("Kaynak video açılamadı.")
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.target_video, fourcc, self.fps, (width, height))
            
            frame_idx = 0

            while self._is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if self.start_frame <= frame_idx <= self.end_frame:
                    frame = inpaint_region(frame, self.roi_rect)
                    
                out.write(frame)
                
                # İlerleme raporla
                if frame_idx % 5 == 0 or frame_idx == total_frames - 1:
                    progress = int((frame_idx / max(1, total_frames - 1)) * 100)
                    self.progress_updated.emit(progress)
                    
                frame_idx += 1
            
            cap.release()
            out.release()
            
            if self._is_running:
                self.inpaint_finished.emit()
                
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False

import subprocess
import tempfile
import uuid
import os
import shutil

class FullVideoExportWorker(QThread):
    progress_updated = pyqtSignal(int)
    export_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, source_video, original_video, target_video, fps):
        super().__init__()
        self.source_video = source_video
        self.original_video = original_video
        self.target_video = target_video
        self.fps = fps
        self._is_running = True

    def get_ffmpeg_path(self):
        import sys
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            exe_path = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
            if os.path.exists(exe_path):
                return exe_path
        return 'ffmpeg'

    def run(self):
        try:
            cap = cv2.VideoCapture(self.source_video)
            if not cap.isOpened():
                self.error_occurred.emit("Kaynak video açılamadı.")
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            temp_processed = os.path.join(tempfile.gettempdir(), f"temp_export_{uuid.uuid4().hex}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_processed, fourcc, self.fps, (width, height))
            
            processed = 0

            while self._is_running:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                out.write(frame)
                processed += 1
                
                # Sadece belli aralıklarla % gönder
                if processed % 5 == 0 or processed == total_frames:
                    progress = int((processed / max(1, total_frames)) * 90) # %90'ı video yazma
                    self.progress_updated.emit(progress)
            
            cap.release()
            out.release()
            
            if not self._is_running:
                if os.path.exists(temp_processed):
                    os.remove(temp_processed)
                return
                
            self.progress_updated.emit(95) # Ses birleştiriliyor
            
            if self.original_video and os.path.exists(self.original_video):
                ffmpeg_exe = self.get_ffmpeg_path()
                cmd = [
                    ffmpeg_exe, '-y', 
                    '-i', temp_processed, 
                    '-i', self.original_video,
                    '-c:v', 'copy', 
                    '-c:a', 'aac', 
                    '-map', '0:v:0', 
                    '-map', '1:a:0?', 
                    '-shortest', 
                    self.target_video
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            else:
                shutil.copy(temp_processed, self.target_video)
                
            if os.path.exists(temp_processed):
                os.remove(temp_processed)
                
            self.progress_updated.emit(100)
            self.export_finished.emit()
                
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self._is_running = False
