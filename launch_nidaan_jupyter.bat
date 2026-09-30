@echo off
call C:\Users\abhay\anaconda3\Scripts\activate.bat C:\Users\abhay\anaconda3
conda activate nidaan
cd /d E:\NidaanKosha-100k
echo.
echo === Working directory: %CD% ===
echo === Python:            %CONDA_PREFIX%\python.exe ===
echo === Environment:       nidaan ===
echo.
jupyter notebook
