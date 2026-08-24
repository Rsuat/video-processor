[TR](#türkçe) | [EN](#english)

<div id="türkçe"></div>

# Video Inpainting Düzenleyici (Video Inpainting Editor)

Videolardaki istenmeyen nesne veya bölgeleri kare bazlı seçip arka plan rengiyle otomatik olarak örtme ve maskeleme (inpainting) işlemi yapmanızı sağlayan profesyonel bir masaüstü uygulamasıdır.

## 🚀 Özellikler
- **Akıcı ve Sade Arayüz:** Siyah alana sürükle-bırak (drag & drop) yöntemiyle anında video yükleme.
- **Orijinal Oranlı Önizleme:** Alt panelde tüm kareleri orijinal en/boy oranları bozulmadan (keep aspect ratio) listeleme ve görüntüleme.
- **Toplu İşleme (Batch Inpainting):** Seçilen başlangıç karesinde çizilen maskenin (ROI), belirlenen bitiş karesine kadar tüm aralıkta otomatik olarak silinmesi/boyanması.
- **Kusursuz Dışa Aktarım:** İşlenen videoyu dışa aktarırken **orijinal sesi koruyarak** kayıpsız `.mp4` formatında kaydetme.
- **Arka Plan İşlemleri:** Video çıkarma, boyama ve ses birleştirme işlemlerinin uygulamayı dondurmadan ayrı thread (QThread) üzerinde yapılması.

## ⚙️ Kurulum ve Çalıştırma

Projenin kendi bilgisayarınızda çalışabilmesi için sisteminizde [Python](https://www.python.org/) ve [FFmpeg](https://ffmpeg.org/) yüklü olmalıdır.

1. Depoyu klonlayın ve proje dizinine gidin:
   ```bash
   git clone <repo-url>
   cd python_project
   ```

2. Gerekli kütüphaneleri sanal ortama kurun:
   ```bash
   pip install -r requirements.txt
   ```

3. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

## 📥 İndirme ve Otomatik Build (Downloads & CI/CD)
Eğer Python ortamıyla uğraşmak istemiyorsanız, önceden derlenmiş çalıştırılabilir sürümleri doğrudan indirebilirsiniz:
- **Windows (.exe) ve Linux Çıktıları:** En güncel sürümleri **[GitHub Actions Artifacts](#)** sayfasından indirip tek tıkla kullanabilirsiniz.

---

<br><br>

<div id="english"></div>

# Video Inpainting Editor

A professional desktop application that allows you to select unwanted objects or regions in a video on a frame-by-frame basis and automatically mask/cover them with the background color (inpainting).

## 🚀 Features
- **Clean & Fluid UI:** Load videos instantly using drag & drop onto the main canvas.
- **Aspect Ratio Maintained Previews:** Lists and previews all frames in the bottom scroll panel while strictly preserving their original aspect ratio.
- **Batch Processing (Inpainting):** Draw a mask (ROI) on a chosen start frame, select an end frame, and the app automatically removes/paints that area across the entire range.
- **Flawless Exporting:** Exports the processed video as an `.mp4` while **preserving the original audio** track perfectly.
- **Background Operations:** Frame extraction, batch inpainting, and audio remuxing are handled asynchronously via QThread without freezing the user interface.

## ⚙️ Installation & Usage

To run the project locally, ensure you have [Python](https://www.python.org/) and [FFmpeg](https://ffmpeg.org/) installed on your system.

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repo-url>
   cd python_project
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## 📥 Downloads & CI/CD (Automatic Builds)
If you prefer not to set up a Python environment, you can download pre-compiled standalone executables:
- **Windows (.exe) and Linux Builds:** Download the latest builds directly from our **[GitHub Actions Artifacts](#)** page and run them with a single click.
