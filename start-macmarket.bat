@echo off
cd C:\Users\ryanm\OneDrive\Documents\GitHub\MacMarket
uvicorn app:app --reload --host 0.0.0.0 --port 9500
pause