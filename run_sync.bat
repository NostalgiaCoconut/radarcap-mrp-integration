@echo off
cd /d "C:\Users\woo09\Desktop\RadarCap\MRP_Integration"
echo %date% %time% - Sync start >> "C:\Users\woo09\Desktop\RadarCap\MRP_Integration\sync_log.txt"
python pipeline\sync.py >> "C:\Users\woo09\Desktop\RadarCap\MRP_Integration\sync_log.txt" 2>&1
echo %date% %time% - Sync done >> "C:\Users\woo09\Desktop\RadarCap\MRP_Integration\sync_log.txt"
