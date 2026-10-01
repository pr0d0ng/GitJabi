from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Google 번역 문서 페이지로 바로 이동
driver.get("https://translate.google.com/?sl=en&tl=ko&op=docs")

time.sleep(5)

print("\n=== 좌표 따기 모드 ===")
print("1) DevTools 콘솔에 좌표가 찍힙니다")
print("2) 번역 버튼 / 다운로드 버튼을 직접 클릭하세요")
print("3) 끝나면 Ctrl+C 로 종료\n")

# 클릭 좌표 콘솔 출력용 JS 주입
driver.execute_script("""
document.addEventListener('click', function(e) {
    console.log(
        '[CLICK]',
        'x=' + e.clientX,
        'y=' + e.clientY,
        'target=' + e.target.tagName
    );
});
""")

# 프로그램이 바로 끝나지 않게 대기
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n좌표 따기 종료")
    driver.quit()
