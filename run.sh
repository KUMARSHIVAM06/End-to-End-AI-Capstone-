#!/bin/bash
echo "============================================================"
echo "  AI Capstone System - Launcher"
echo "============================================================"
echo ""
echo "  1) Run Demo Script        (no hardware required)"
echo "  2) Launch CLI             (voice or keyboard)"
echo "  3) Launch GUI             (Tkinter)"
echo "  4) Run Tests              (pytest)"
echo "  5) Install Dependencies"
echo "  6) Exit"
echo ""
read -p "Enter choice (1-6): " choice

case $choice in
  1) python3 demo/demo_script.py --slow ;;
  2) python3 cli/main_cli.py --simulated --no-mic ;;
  3) python3 gui/main_gui.py --simulated --no-tts ;;
  4) python3 -m pytest tests/ -v ;;
  5) pip3 install -r requirements.txt ;;
  6) exit 0 ;;
  *) echo "Invalid choice." ;;
esac
