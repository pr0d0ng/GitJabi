import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===================== 설정 =====================
INPUT_DIR = r"temp/icsi-corpus/dialogue_xlsx"
DOWNLOAD_DIR = r"temp/icsi-corpus/dialogue_xlsx_kor"
URL = "https://translate.google.com/?sl=en&tl=ko&op=docs"
BTN_TRANSLATE = (1129, 341)  # 번역 버튼 좌표

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
DOWNLOAD_DIR = str(Path(DOWNLOAD_DIR).resolve())

# ===================== 유틸 =====================
def click_by_xy(driver, x, y):
    driver.execute_script(
        f"""
        const el = document.elementFromPoint({x}, {y});
        if (!el) {{
            throw new Error("elementFromPoint returned null");
        }}
        el.click();
        """
    )


def open_docs_page_and_get_file_input(driver, timeout=40) -> WebElement:
    # Google이 op=docs를 op=translate로 돌려도, 문서 탭 버튼을 직접 눌러 모드 전환한다.
    driver.get("https://translate.google.com/?sl=en&tl=ko&op=translate")
    wait_local = WebDriverWait(driver, timeout)
    wait_local.until(EC.presence_of_element_located((By.TAG_NAME, "button")))

    clicked = driver.execute_script(
        """
        const isDocs = (s) => {
            const t = (s || '').toLowerCase();
            return t.includes('문서') || t.includes('documents') || t.includes('document');
        };
        const buttons = [...document.querySelectorAll('button')];
        for (const b of buttons) {
            const mix = (b.innerText || '') + ' ' + (b.getAttribute('aria-label') || '');
            if (isDocs(mix)) {
                b.click();
                return true;
            }
        }
        return false;
        """
    )
    if not clicked:
        raise TimeoutError("문서 탭 버튼 탐색 실패")

    def _pick_input(d):
        inputs = d.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for el in inputs:
            if el.is_enabled():
                return el
        return False

    file_input = wait_local.until(_pick_input)
    return file_input


def snapshot_download_dir():
    snap = {}
    for name in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, name)
        if os.path.isfile(path):
            st = os.stat(path)
            snap[name] = (st.st_size, st.st_mtime)
    return snap


def wait_download_new_file(before_snapshot, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        for name in os.listdir(DOWNLOAD_DIR):
            if name.endswith(".crdownload"):
                continue
            path = os.path.join(DOWNLOAD_DIR, name)
            if not os.path.isfile(path):
                continue
            st = os.stat(path)
            now_state = (st.st_size, st.st_mtime)
            if name not in before_snapshot:
                return name
            if before_snapshot[name] != now_state:
                return name
        time.sleep(0.5)
    raise TimeoutError("다운로드 파일 생성 감지 실패")


def wait_download_button(driver, timeout=300):
    end = time.time() + timeout
    while time.time() < end:
        target = driver.execute_script(
            """
            const candidates = [...document.querySelectorAll("button, [role='button']")];
            for (const el of candidates) {
                if (el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
                const s = getComputedStyle(el);
                if (s.display === 'none' || s.visibility === 'hidden') continue;
                if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
                const text = ((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '')).toLowerCase();
                if (
                    text.includes('다운로드') ||
                    text.includes('download') ||
                    text.includes('내려받기')
                ) {
                    return el;
                }
            }
            return null;
            """
        )
        if target:
            return target
        time.sleep(0.7)
    raise TimeoutError("다운로드 버튼 탐색 실패")

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
MAX_RETRIES_PER_FILE = 3

try:
    files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".xlsx")])
    if not files:
        raise RuntimeError("입력 xlsx 파일 없음")

    start_from = os.getenv("START_FROM", "").strip()
    if start_from:
        if start_from not in files:
            raise RuntimeError(f"START_FROM 파일을 찾을 수 없음: {start_from}")
        start_idx = files.index(start_from)
        files = files[start_idx:]
        print(f"START_FROM 적용: {start_from}부터 처리 ({len(files)}개)")

    max_files = int(os.getenv("MAX_FILES", "0"))
    if max_files > 0:
        files = files[:max_files]
        print(f"MAX_FILES 적용: {len(files)}개만 처리")

    skip_existing = os.getenv("SKIP_EXISTING", "0").strip().lower() in {"1", "true", "yes", "y"}
    if skip_existing:
        print("SKIP_EXISTING 적용: 출력 파일이 있으면 건너뜀")

    for fname in files:
        if skip_existing:
            out_path = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(out_path):
                print(f"\n[스킵] {fname} (이미 존재)")
                continue

        print(f"\n[처리] {fname}")
        src = str(Path(INPUT_DIR, fname).resolve())
        done = False
        last_error = None

        for attempt in range(1, MAX_RETRIES_PER_FILE + 1):
            try:
                print(f" - 시도 {attempt}/{MAX_RETRIES_PER_FILE}")
                file_input = open_docs_page_and_get_file_input(driver)
                print("   - 문서 탭 진입")

                # 🔹 이전 다운로드 상태 기억
                before_files = snapshot_download_dir()

                # 🔹 업로드 input 확보
                file_input.send_keys(src)
                time.sleep(1.5)

                # 🔹 번역 버튼 클릭
                click_by_xy(driver, *BTN_TRANSLATE)
                print("   - 번역 버튼 클릭")

                # 🔹 번역 완료 대기
                download_btn = wait_download_button(driver, timeout=300)
                print("   - 번역 완료 감지")

                # 🔹 다운로드 버튼 클릭
                driver.execute_script("arguments[0].click();", download_btn)
                print("   - 번역 다운로드 클릭")

                # 🔹 실제 파일 생성 감지
                downloaded_name = wait_download_new_file(before_files)
                print(f"   - 다운로드 완료: {downloaded_name}")

                # 🔹 파일명 유지 (덮어쓰기)
                downloaded_path = os.path.join(DOWNLOAD_DIR, downloaded_name)
                target_path = os.path.join(DOWNLOAD_DIR, fname)
                if os.path.abspath(downloaded_path) != os.path.abspath(target_path):
                    os.replace(downloaded_path, target_path)

                print("   - 파일명 유지 완료")
                done = True
                break

            except Exception as ex:
                last_error = ex
                print(f"   - 재시도 필요: {ex}")
                time.sleep(6)

        if not done:
            raise RuntimeError(f"{fname} 처리 실패: {last_error}")

        # 🔹 다음 파일 전 세션 리셋
        print(" - 페이지 새로고침(세션 리셋)")
        driver.get(URL)
        time.sleep(5)

except Exception as e:
    print("오류 발생:", e)

finally:
    driver.quit()
    print("\n작업 종료")
