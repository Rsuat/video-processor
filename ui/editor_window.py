import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QFileDialog, QMessageBox, QGraphicsRectItem, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QImage, QPixmap, QPen, QColor, QPainter

from utils.image_processing import inpaint_region

class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Modes: "pan" or "select"
        self.mode = "pan"
        
        # Pan variables
        self._is_panning = False
        self._pan_start_pos = QPointF()
        
        # Select variables
        self._is_selecting = False
        self._selection_start_pos = QPointF()
        self.selection_rect_item = None

    def set_mode(self, mode):
        self.mode = mode
        if self.mode == "pan":
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.mode == "select":
            self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "pan":
                self._is_panning = True
                self._pan_start_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif self.mode == "select":
                self._is_selecting = True
                self._selection_start_pos = self.mapToScene(event.pos())
                
                # Mevcut seçimi temizle
                if self.selection_rect_item:
                    self.scene().removeItem(self.selection_rect_item)
                
                # Yeni seçim oluştur
                self.selection_rect_item = QGraphicsRectItem(QRectF(self._selection_start_pos, self._selection_start_pos))
                pen = QPen(QColor(255, 0, 0))
                pen.setWidth(2)
                self.selection_rect_item.setPen(pen)
                self.selection_rect_item.setZValue(100) # En üstte görünsün
                self.scene().addItem(self.selection_rect_item)
                
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning and self.mode == "pan":
            delta = event.position() - self._pan_start_pos
            self._pan_start_pos = event.position()
            
            # Kaydırma işlemi
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(int(h_bar.value() - delta.x()))
            v_bar.setValue(int(v_bar.value() - delta.y()))
            
        elif self._is_selecting and self.mode == "select" and self.selection_rect_item:
            current_pos = self.mapToScene(event.pos())
            rect = QRectF(self._selection_start_pos, current_pos).normalized()
            self.selection_rect_item.setRect(rect)
            
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.mode == "pan":
                self._is_panning = False
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            elif self.mode == "select":
                self._is_selecting = False
                
        super().mouseReleaseEvent(event)
        
    def get_selected_rect(self):
        if self.selection_rect_item:
            return self.selection_rect_item.rect()
        return None

    def clear_selection(self):
        if self.selection_rect_item:
            self.scene().removeItem(self.selection_rect_item)
            self.selection_rect_item = None


class EditorWindow(QMainWindow):
    roi_selected = pyqtSignal(tuple)

    def __init__(self, cv_image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detaylı Kare Düzenleyici")
        self.resize(800, 600)
        
        self.cv_image = cv_image.copy() # BGR image
        self.setup_ui()
        self.display_image()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Butonlar Paneli
        top_panel = QHBoxLayout()
        
        self.btn_pan = QPushButton("Pan Modu")
        self.btn_pan.setCheckable(True)
        self.btn_pan.setChecked(True)
        
        self.btn_select = QPushButton("Seçim Modu (ROI)")
        self.btn_select.setCheckable(True)
        
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.btn_pan)
        mode_group.addButton(self.btn_select)
        mode_group.buttonClicked.connect(self.on_mode_changed)
        
        self.btn_confirm = QPushButton("Seçimi Onayla")
        self.btn_confirm.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_confirm.clicked.connect(self.confirm_roi)
        
        top_panel.addWidget(self.btn_pan)
        top_panel.addWidget(self.btn_select)
        top_panel.addStretch()
        top_panel.addWidget(self.btn_confirm)
        
        # Graphics View ve Scene
        self.scene = QGraphicsScene()
        self.view = InteractiveGraphicsView(self.scene)
        self.view.set_mode("pan")
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        main_layout.addLayout(top_panel)
        main_layout.addWidget(self.view, 1)

    def display_image(self):
        rgb_image = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        pixmap = QPixmap.fromImage(q_img)
        self.pixmap_item.setPixmap(pixmap)
        
        # Scene boyutunu güncelle
        self.scene.setSceneRect(0, 0, w, h)
        
        # İlk açılışta görüntü sığsın diye scale yap
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def on_mode_changed(self, button):
        if button == self.btn_pan:
            self.view.set_mode("pan")
        elif button == self.btn_select:
            self.view.set_mode("select")

    def confirm_roi(self):
        rect_f = self.view.get_selected_rect()
        if not rect_f:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce 'Seçim Modu' ile bir alan belirleyin.")
            return
            
        x = int(rect_f.x())
        y = int(rect_f.y())
        w = int(rect_f.width())
        h = int(rect_f.height())
        
        # Sınır kontrolü
        img_h, img_w = self.cv_image.shape[:2]
        x = max(0, x)
        y = max(0, y)
        w = min(w, img_w - x)
        h = min(h, img_h - y)
        
        if w <= 0 or h <= 0:
            QMessageBox.warning(self, "Uyarı", "Geçersiz seçim alanı.")
            return
            
        roi_rect = (x, y, w, h)
        self.roi_selected.emit(roi_rect)
        self.close()
