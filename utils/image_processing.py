import cv2
import numpy as np

def inpaint_region(image, roi_rect):
    """
    OpenCV inpaint algoritmasını kullanarak seçili bölgeyi (ROI) etrafındaki piksellerle
    pürüzsüz bir şekilde doldurur (silme efekti).
    
    :param image: İşlenecek görüntü (numpy dizisi, BGR formatında)
    :param roi_rect: (x, y, w, h) formatında dikdörtgen bölge
    :return: İşlenmiş yeni görüntü
    """
    x, y, w, h = roi_rect
    
    # Görüntü boyutlarında, içi tamamen 0 (siyah) olan bir maske oluştur
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    # Silinecek alanı (ROI) maskede 255 (beyaz) yap
    mask[y:y+h, x:x+w] = 255
    
    # inpaintRadius: Etraftan ne kadar piksel alınacağı (3-5 genelde iyi sonuç verir)
    # INPAINT_TELEA veya INPAINT_NS kullanılabilir.
    inpainted_img = cv2.inpaint(image, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    
    return inpainted_img

