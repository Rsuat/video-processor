import cv2
import os
import tempfile
import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QScrollArea, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from utils.video_workers import FrameExtractorWorker, BatchInpaintWorker, FullVideoExportWorker
from ui.editor_window import EditorWindow

class ThumbnailLabel(QLabel):
    clicked = pyqtSignal(int)

    def __init__(self, frame_idx, parent=None):
        super().__init__(parent)
        self.frame_idx = frame_idx
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: 2px solid transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.frame_idx)
            self.update_style(selected=True)
            super().mousePressEvent(event)
            
    def update_style(self, selected=False):
        if selected:
            self.setStyleSheet("border: 2px solid #0078D7;")
        else:
            self.setStyleSheet("border: 2px solid transparent;")


class DropVideoLabel(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #000;")
        self.setMinimumSize(640, 360)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                self.file_dropped.emit(file_path)
                return
            else:
                print(f"Geçersiz dosya formatı yoksayıldı: {file_path}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Oynatıcı ve Toplu Boyama")
        self.resize(1024, 768)

        self.video_path = None
        self.original_video_path = None
        self.cap = None
        self.is_playing = False
        self.fps = 30
        self.current_cv_frame = None
        self.current_selected_idx = None
        
        self.start_frame_idx = None
        self.roi_rect = None
        
        self.batch_worker = None
        self.extractor_worker = None
        self.full_exporter_worker = None
        self.thumbnails = []
        self.temp_files = []
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Üst Panel (Butonlar)
        top_panel = QHBoxLayout()
        
        self.btn_play_pause = QPushButton("Oynat")
        self.btn_play_pause.setMinimumHeight(40)
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self.toggle_play)

        self.btn_set_start = QPushButton("Başlangıç Görseli Seç")
        self.btn_set_start.setMinimumHeight(40)
        self.btn_set_start.setEnabled(False)
        self.btn_set_start.clicked.connect(self.set_start_image)
        
        self.btn_set_end = QPushButton("Bitiş Görseli Seç (Toplu Boya)")
        self.btn_set_end.setMinimumHeight(40)
        self.btn_set_end.setEnabled(False)
        self.btn_set_end.clicked.connect(self.set_end_image_and_process)
        
        self.btn_export = QPushButton("Videoyu Dışa Aktar")
        self.btn_export.setMinimumHeight(40)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_video)

        top_panel.addWidget(self.btn_play_pause)
        top_panel.addWidget(self.btn_set_start)
        top_panel.addWidget(self.btn_set_end)
        top_panel.addWidget(self.btn_export)
        top_panel.addStretch()

        # Ana Video Ekranı
        self.video_label = DropVideoLabel()
        self.video_label.file_dropped.connect(self.upload_video_from_user)
        
        # Alt Panel (Thumbnails Scroll Area)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(180)
        
        self.scroll_content = QWidget()
        self.thumbnails_layout = QHBoxLayout(self.scroll_content)
        self.thumbnails_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.thumbnails_layout.setContentsMargins(5, 5, 5, 5)
        self.thumbnails_layout.setSpacing(10)
        self.scroll_area.setWidget(self.scroll_content)

        main_layout.addLayout(top_panel)
        main_layout.addWidget(self.video_label, 1)
        main_layout.addWidget(self.scroll_area)

    def upload_video_from_user(self, path):
        self.original_video_path = path
        self.load_video(path)

    def load_video(self, path):
        self.stop_playback()
        if self.cap:
            self.cap.release()
            
        if self.extractor_worker:
            self.extractor_worker.stop()
            self.extractor_worker.wait()
            
        if self.full_exporter_worker:
            self.full_exporter_worker.stop()
            self.full_exporter_worker.wait()
            
        self.clear_thumbnails()
        self.start_frame_idx = None
        self.roi_rect = None
        self.current_selected_idx = None
        
        self.video_path = path
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Hata", "Video açılamadı!")
            return

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
            
        self.show_frame_preview(0)
        
        self.btn_play_pause.setEnabled(True)
        self.btn_play_pause.setText("Oynat")
        self.btn_set_start.setEnabled(True)
        self.btn_set_end.setEnabled(False) # Başlangıç seçilene kadar kapalı
        self.btn_export.setEnabled(True)

        self.extractor_worker = FrameExtractorWorker(self.video_path, target_height=150)
        self.extractor_worker.frame_extracted.connect(self.add_thumbnail)
        self.extractor_worker.error_occurred.connect(self.show_error)
        self.extractor_worker.start()

    def toggle_play(self):
        if not self.cap or not self.cap.isOpened():
            return
            
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def start_playback(self):
        self.is_playing = True
        self.btn_play_pause.setText("Durdur")
        delay = int(1000 / self.fps)
        self.timer.start(delay)

    def stop_playback(self):
        self.is_playing = False
        self.btn_play_pause.setText("Oynat")
        self.timer.stop()

    def next_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.display_cv_frame(frame)
            else:
                self.stop_playback()
                self.show_frame_preview(0)

    def display_cv_frame(self, frame):
        self.current_cv_frame = frame.copy()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def add_thumbnail(self, frame_idx, q_img):
        lbl = ThumbnailLabel(frame_idx)
        lbl.setPixmap(QPixmap.fromImage(q_img))
        lbl.clicked.connect(self.on_thumbnail_clicked)
        
        self.thumbnails_layout.addWidget(lbl)
        self.thumbnails.append(lbl)

    def clear_thumbnails(self):
        for i in reversed(range(self.thumbnails_layout.count())): 
            widget_to_remove = self.thumbnails_layout.itemAt(i).widget()
            self.thumbnails_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
        self.thumbnails.clear()

    def on_thumbnail_clicked(self, frame_idx):
        self.stop_playback()
        self.current_selected_idx = frame_idx
        
        for thumb in self.thumbnails:
            if thumb.frame_idx == frame_idx:
                thumb.update_style(selected=True)
            else:
                thumb.update_style(selected=False)
                
        self.show_frame_preview(frame_idx)
        
    def set_start_image(self):
        if self.current_cv_frame is not None and self.current_selected_idx is not None:
            self.stop_playback()
            self.editor = EditorWindow(self.current_cv_frame, self)
            self.editor.roi_selected.connect(self.on_roi_selected)
            self.editor.show()
        else:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce alt kısımdan bir başlangıç karesi seçin.")

    def on_roi_selected(self, roi_rect):
        self.roi_rect = roi_rect
        self.start_frame_idx = self.current_selected_idx
        self.btn_set_end.setEnabled(True)
        QMessageBox.information(self, "Bilgi", "Başlangıç karesi ve alan (ROI) belirlendi. Şimdi bitiş karesini seçip işlemi başlatın.")

    def set_end_image_and_process(self):
        if self.roi_rect is None or self.start_frame_idx is None:
            QMessageBox.warning(self, "Uyarı", "Önce bir Başlangıç Görseli ayarlamalısınız.")
            return
            
        if self.current_selected_idx is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen alt kısımdan bir bitiş karesi seçin.")
            return
            
        end_idx = self.current_selected_idx
        if end_idx <= self.start_frame_idx:
            QMessageBox.warning(self, "Uyarı", "Bitiş karesi başlangıç karesinden sonra olmalıdır.")
            return

        # Toplu İşleme Başlat
        target_path = os.path.join(tempfile.gettempdir(), f"temp_edited_{uuid.uuid4().hex}.mp4")
        self.temp_files.append(target_path)
        
        self.btn_set_start.setEnabled(False)
        self.btn_set_end.setEnabled(False)
        self.btn_play_pause.setEnabled(False)
        self.setWindowTitle("Toplu Boyama İşleniyor... Lütfen bekleyin.")
        
        self.batch_worker = BatchInpaintWorker(
            self.video_path, target_path, 
            self.start_frame_idx, end_idx, self.roi_rect, self.fps
        )
        self.batch_worker.progress_updated.connect(self.on_batch_progress)
        self.batch_worker.inpaint_finished.connect(lambda: self.on_batch_finished(target_path))
        self.batch_worker.error_occurred.connect(self.show_error)
        self.batch_worker.start()

    def on_batch_progress(self, p):
        self.setWindowTitle(f"Toplu Boyama İşleniyor... %{p}")

    def on_batch_finished(self, new_video_path):
        self.setWindowTitle("Video Oynatıcı ve Toplu Boyama")
        QMessageBox.information(self, "İşlem Tamamlandı", "Belirlenen aralıktaki tüm kareler başarıyla boyandı/işlendi.")
        
        # Yeni videoyu yükleyerek ekranı sessizce yenile
        self.load_video(new_video_path)

    def show_frame_preview(self, frame_idx):
        if not self.cap or not self.cap.isOpened():
            return
            
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            self.display_cv_frame(frame)

    def show_error(self, err_msg):
        QMessageBox.critical(self, "Hata", err_msg)
        self.setWindowTitle("Video Oynatıcı ve Toplu Boyama")
        self.btn_set_start.setEnabled(True)
        self.btn_set_end.setEnabled(True)
        self.btn_play_pause.setEnabled(True)
        self.btn_export.setEnabled(True)
        
    def export_video(self):
        if not self.video_path:
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Videoyu Dışa Aktar", "final_video.mp4", "Video Dosyaları (*.mp4)"
        )
        if file_name:
            self.btn_export.setEnabled(False)
            self.setWindowTitle("Video kaydediliyor... Lütfen bekleyin.")
            
            self.full_exporter_worker = FullVideoExportWorker(self.video_path, self.original_video_path, file_name, self.fps)
            self.full_exporter_worker.progress_updated.connect(lambda p: self.setWindowTitle(f"Video kaydediliyor... %{p}"))
            self.full_exporter_worker.export_finished.connect(self.on_full_export_finished)
            self.full_exporter_worker.error_occurred.connect(self.show_error)
            self.full_exporter_worker.start()

    def on_full_export_finished(self):
        self.setWindowTitle("Video Oynatıcı ve Toplu Boyama")
        self.btn_export.setEnabled(True)
        QMessageBox.information(self, "Bilgi", "Video ve ses başarıyla birleştirilerek kaydedildi!")
        
    def closeEvent(self, event):
        self.stop_playback()
        if self.cap:
            self.cap.release()
        if self.extractor_worker:
            self.extractor_worker.stop()
            self.extractor_worker.wait()
        if self.batch_worker:
            self.batch_worker.stop()
            self.batch_worker.wait()
        if self.full_exporter_worker:
            self.full_exporter_worker.stop()
            self.full_exporter_worker.wait()
            
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
                    
        super().closeEvent(event)
