@echo off
echo ========================================================
echo Video Oynatici - Windows Build (.exe) Baslatiliyor
echo ========================================================

echo 1. Gerekli paketler yukleniyor...
pip install -r requirements.txt

echo 2. PyInstaller ile derleme yapiliyor...
echo Lutfen bekleyin, bu islem biraz surebilir...

rem --noconsole: Arka planda siyah konsol penceresini gizler
rem --onefile: Tum bagimliliklari tek bir .exe dosyasinda toplar
rem --add-binary "ffmpeg.exe;.": ffmpeg.exe dosyasini paketin ana dizinine ekler
pyinstaller --noconsole --onefile --add-binary "ffmpeg.exe;." --name "VideoEditor" main.py

echo.
echo ========================================================
echo Islem Tamamlandi! 
echo Olusturulan program "dist/VideoEditor.exe" yolundadir.
echo ========================================================
pause
