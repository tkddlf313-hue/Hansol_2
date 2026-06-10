import subprocess
import threading
import webbrowser
import time
import sys
import os

URL  = "http://localhost:8501"
PORT = 8501

def open_browser():
    time.sleep(3)          # Streamlit이 뜰 때까지 대기
    webbrowser.open(URL)

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 45)
    print("   📈 오늘의 종목 대시보드 시작")
    print(f"   주소: {URL}")
    print("   종료: 이 창을 닫거나 Ctrl+C")
    print("=" * 45)

    threading.Thread(target=open_browser, daemon=True).start()

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(PORT),
         "--server.headless", "true"],
    )

if __name__ == "__main__":
    main()
