# TCELABLINK – QR-Based Laboratory Equipment Management & Tracking System

A Flask-based working prototype for digitally managing laboratory equipment.

## What's in the prototype
- Digital equipment inventory with unique IDs
- Real, scannable QR codes for each item (opens its record)
- Auto-overdue detection based on due dates
- Equipment lifecycle: Available → Issued → Returned
- Defective and Under Maintenance statuses with Restore
- Staff dashboard with issue / return / defect / maintenance actions
- Student portal with live search
- Full status history log for every item
- Persistent data stored in `data.json`

## Setup
```bash
pip install flask "qrcode[pil]"
python app.py
```

Open http://127.0.0.1:5000

## Demo tip — scanning the QR with your phone
1. Find your laptop's local Wi-Fi IP:
   - Windows: `ipconfig` → look for "IPv4 Address"
   - Mac/Linux: `ifconfig` → look for `inet` on the Wi-Fi adapter
2. In `app.py`, set `BASE_URL = "http://<your-ip>:5000"` (e.g. `http://192.168.1.7:5000`)
3. Restart the app and rescan the QR — it will open on your phone.

## Notes
- Data is persisted in `data.json` (created automatically on first run).
- Delete `data.json` to reset back to the sample records.
- This is a design-thinking prototype, not a production system.