import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== 설정 =====================
INPUT_DIR = r"temp\dialogue_xlsx"
DOWNLOAD_DIR = r"temp\dialogue_xlsx_kor"
URL = "https://translate.google.com/?sl=en&tl=ko&op=docs"

# 🔴 반드시 본인이 딴 좌표 사용
BTN_TRANSLATE = (1129, 341)   # 번역 버튼
BTN_DOWNLOAD  = (1136, 275)   # 번역 다운로드 버튼

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
DOWNLOAD_DIR = str(Path(DOWNLOAD_DIR).resolve())

# ===================== 유틸 =====================
def click_by_xy(driver, x, y):
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(
        driver.find_element(By.TAG_NAME, "body"), 0, 0
    ).perform()
    actions.move_by_offset(x, y).click().perform()
    actions.reset_actions()

def wait_download_new_file(before_files, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        cur = set(os.listdir(DOWNLOAD_DIR))
        diff = cur - before_files
        for f in diff:
            if not f.endswith(".crdownload"):
                return f
        time.sleep(0.5)
    raise TimeoutError("다운로드 파일 생성 감지 실패")

def wait_translate_done(driver, timeout=300):
    end = time.time() + timeout
    while time.time() < end:
        ready = driver.execute_script("""
            const btns = [...document.querySelectorAll("button")];
            const btn = btns.find(b => 
                b.innerText.includes("다운로드") || b.innerText.includes("Download")
            );
            if (!btn) return false;
            if (btn.disabled) return false;
            const s = getComputedStyle(btn);
            return !(s.display === 'none' || s.visibility === 'hidden');
        """)
        if ready:
            return
        time.sleep(0.7)
    raise TimeoutError("번역 완료 감지 실패")

# ===================== 드라이버 =====================
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--lang=ko-KR")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)

try:
    driver.get(URL)

    files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".xlsx")])
    if not files:
        raise RuntimeError("입력 xlsx 파일 없음")

    for fname in files:
        print(f"\n[처리] {fname}")
        src = str(Path(INPUT_DIR, fname).resolve())

        # 🔹 이전 다운로드 상태 기억
        before_files = set(os.listdir(DOWNLOAD_DIR))

        # 🔹 업로드 input 확보
        file_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(src)
        time.sleep(1.5)

        # 🔹 번역 버튼 클릭
        click_by_xy(driver, *BTN_TRANSLATE)
        print(" - 번역 버튼 클릭")

        # 🔹 번역 완료 대기
        wait_translate_done(driver)
        print(" - 번역 완료 감지")

        # 🔹 다운로드 버튼 클릭
        click_by_xy(driver, *BTN_DOWNLOAD)
        print(" - 번역 다운로드 클릭")

        # 🔹 실제 파일 생성 감지
        downloaded_name = wait_download_new_file(before_files)
        print(f" - 다운로드 완료: {downloaded_name}")

        # 🔹 파일명 유지 (덮어쓰기)
        downloaded_path = os.path.join(DOWNLOAD_DIR, downloaded_name)
        target_path = os.path.join(DOWNLOAD_DIR, fname)

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(downloaded_path, target_path)

        print(" - 파일명 유지 완료")

        # 🔹 🔥 세션 리셋 (핵심)
        print(" - 페이지 새로고침(세션 리셋)")
        driver.refresh()
        time.sleep(5)

except Exception as e:
    print("❌ 오류 발생:", e)

finally:
    driver.quit()
    print("\n작업 종료")
