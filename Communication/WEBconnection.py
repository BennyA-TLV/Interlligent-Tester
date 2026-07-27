from selenium import webdriver
from bs4 import BeautifulSoup
from Communication.Connection import *
from selenium.common import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from pathlib import Path
import tempfile
import psutil
import winreg
import shutil
import threading
import ctypes
import random
import sys
import time
import re
import os


# Created by Benny Aberman - 054-3220104
# WEB connection functions
    # The get keysight newest software details function
    # The get latest keysight software version for the OS function
    # The get latest firmware version for the OS function
    # The get keysight software versions with the OS details function
    # The download the latest firmware version for the OS from url function
    # The numan typing function
    # The popup massages to the user function
    # The popup massage that is waiting for the user  function
    # the check download function


# The get keysight newest software details function - the function open the chrome, in show mode, to the take all the newest software details
def get_keysight_software_details(url, retries=3):
    results = []
    driver = None
    profile_dir = None

    options = uc.ChromeOptions()
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--start-maximized')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--remote-debugging-port=0")
    profile_dir = tempfile.mkdtemp(prefix="chrome_keysight_")
    options.add_argument(f"--user-data-dir={profile_dir}")

    for attempt in range(retries + 1):
        driver = None
        try:
            chrome_version = get_chrome_major_version()
            if chrome_version:
                driver = uc.Chrome(version_main=chrome_version, options=options, use_subprocess=True)
            else:
                driver = uc.Chrome(options=options, use_subprocess=True)

            driver.set_page_load_timeout(90)
            driver.set_window_size(400, 300)
            driver.get(url)

            WebDriverWait(driver, 40).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            page_text = soup.get_text(separator=' ')

            if any(msg in page_text.lower() for msg in ["access denied", "security check", "captcha", "forbidden"]):
                raise PermissionError("Access blocked by website (Bot detection)")

            all_versions = re.findall(r'[A-Z]\.\d{1,2}\.\d{1,2}', page_text)
            latest_rev = sorted(list(set(all_versions)), reverse=True)[0] if all_versions else "Not found"

            found_os = [os for os in ["Windows 11", "Windows 10"] if os in page_text]

            return {
                "revision": latest_rev,
                "os": ", ".join(found_os) if found_os else "Not found",
                "status": "success"
            }

        except TimeoutException:
            print(f"Attempt {attempt + 1}: Timeout occurred.")
        except PermissionError as e:
            print(f"Attempt {attempt + 1}: {e}")
        except Exception as e:
            print(f"Attempt {attempt + 1}: Unexpected error - {str(e)}")

        finally:
            safe_close_driver(driver)

        if attempt < retries:
            time.sleep(20)

    return {"error": "Failed to retrieve data after multiple attempts", "status": "failed"}

def cloudflare_visible(driver):
    try:
        page_text = driver.page_source.lower()
        title = (driver.title or "").lower()

        indicators = [
            "verify you are human",
            "verifying your connection",
            "security check",
            "just a moment",
        ]

        if any(text in page_text or text in title for text in indicators):
            return True

        frames = driver.find_elements(By.TAG_NAME, "iframe")

        for frame in frames:
            src = (frame.get_attribute("src") or "").lower()
            title_attr = (frame.get_attribute("title") or "").lower()

            if (
                "cloudflare" in src
                or "turnstile" in src
                or "challenge" in src
                or "cloudflare" in title_attr
                or "challenge" in title_attr
            ):
                return True

    except Exception:
        pass

    return False

def wait_for_cloudflare_if_needed(driver, timeout=120):

    if not cloudflare_visible(driver):
        return True

    print(" > Cloudflare verification detected.")
    print(" > Please complete the verification manually in Chrome.")

    show_popup_non_blocking(
        "Cloudflare security verification detected.\n"
        "Please complete 'Verify you are human' manually in Chrome.\n"
        "The automation will continue automatically afterward.",
        "Action Required",
        60
    )

    start_time = time.time()

    while time.time() - start_time < timeout:
        if not cloudflare_visible(driver):
            print(" > Cloudflare verification completed.")
            time.sleep(3)
            return True

        time.sleep(2)

    print(" > Timeout waiting for Cloudflare verification.")
    return False

# The get keysight software versions with the OS details function - the function open the chrome, in show mode, to the take all the software details
"""def get_keysight_versions_with_os(url):
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=146, use_subprocess=True)
    driver.set_window_size(400, 300)

    results = []
    try:
        driver.get(url)
        time.sleep(8)

        try:
            tab = driver.find_element(By.XPATH, "//li[contains(., 'Previous Versions')]")
            driver.execute_script("arguments.click();", tab)
            time.sleep(5)
        except:
            pass

        full_html = driver.page_source
        chunks = full_html.split('class="accordion1"')

        for chunk in chunks[1:]:
            v_match = re.search(r'A\.\d+\.\d+', chunk)
            v_num = v_match.group(0) if v_match else None

            if v_num:
                raw_os = re.findall(r'Windows\s*(?:11|10|8|7|Server|XP)', chunk, re.I)
                clean_os = sorted(list(set([" ".join(o.split()).strip() for o in raw_os])))

                link_match = re.search(r'href=["\']([^"\']*(?:software-detail|download|sw-detail)[^"\']*)["\']', chunk,
                                       re.I)
                download_link = link_match.group(1) if link_match else f"{url}?version={v_num}"
                if download_link.startswith('/'):
                    download_link = "https://keysight.com" + download_link

                results.append({
                    "Version": v_num,
                    "OS": clean_os,
                    "Download": download_link
                })
    finally:
        try:
            safe_close_driver(driver)
        except:
            pass

    return results"""

# The get latest keysight software version for the OS function - the function take all the software details and print the latest one
def get_latest_for_os(data, target_os):
    if not data: return None

    search_term = " ".join(target_os.lower().replace("win ", "windows ").split()).strip()
    filtered = [i for i in data if any(search_term in " ".join(i['OS']).lower() for _ in [1])]

    if not filtered:
        print(f"No version found for {target_os}")
        return None

    filtered.sort(key=lambda x: [int(n) for n in re.findall(r'\d+', x['Version'])], reverse=True)
    latest = filtered[0]

    return latest

def parse_keysight_version(version):

    match = re.fullmatch(r"\s*([A-Za-z])\.(\d+)(?:\.(\d+))?\s*", version)

    if not match:
        raise ValueError(f"Invalid Keysight version: {version}")

    return (
        match.group(1).upper(),
        int(match.group(2)),
        int(match.group(3) or 0)
    )


def normalize_os(value):
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def os_is_compatible(target_os, supported_os_list):
    target = normalize_os(target_os)

    return any(
        target == normalize_os(supported_os)
        or target in normalize_os(supported_os)
        or normalize_os(supported_os) in target
        for supported_os in supported_os_list
    )


def version_sort_key(version):

    prefix, major, patch = parse_keysight_version(version)

    prefix_number = ord(prefix) - ord("A")

    return prefix_number, major, patch


def get_upgrade_versions_for_os(current_version, target_os, url):

    all_versions = get_keysight_versions_with_os(url)
    current_prefix, current_major, current_patch = parse_keysight_version(current_version)
    current_key = version_sort_key(current_version)
    best_version_per_stage = {}

    for item in all_versions:
        version = item.get("Version")
        supported_os = item.get("OS", [])

        if not version:
            continue

        if not os_is_compatible(target_os, supported_os):
            continue

        try:
            prefix, major, patch = parse_keysight_version(version)
            candidate_key = version_sort_key(version)
        except ValueError:
            continue

        if candidate_key <= current_key:
            continue

        #if prefix == current_prefix and major == current_major:
            continue

        stage = (prefix, major)
        existing = best_version_per_stage.get(stage)

        if existing is None or patch > existing["Patch"]:
            best_version_per_stage[stage] = {
                "Version": version,
                "Patch": patch,
                "OS": supported_os
            }


    sorted_stages = sorted(
        best_version_per_stage,
        key=lambda stage: (
            ord(stage[0]) - ord("A"),
            stage[1]
        )
    )

    return [
        best_version_per_stage[stage]["Version"]
        for stage in sorted_stages
    ]

# The get latest firmware version for the OS function
def get_latest_version_for_os(target_os, url):
    all_versions = get_keysight_versions_with_os(url)

    matching_versions = [v['Version'] for v in all_versions if target_os in v['OS']]

    if not matching_versions:
        return None

    matching_versions.sort(key=lambda s: [int(u) for u in re.findall(r'\d+', s)], reverse=True)

    return matching_versions[0]

def get_chrome_major_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")

        return int(version.split(".")[0])
    except:
        return None

# The get keysight software versions with the OS details function
def get_keysight_versions_with_os(url):
    global results
    options = uc.ChromeOptions()
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--start-maximized')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--remote-debugging-port=0")
    profile_dir = tempfile.mkdtemp(prefix="chrome_keysight_")
    options.add_argument(f"--user-data-dir={profile_dir}")
    driver = None

    try:
        chrome_version = get_chrome_major_version()
        if chrome_version:
            driver = uc.Chrome(version_main=chrome_version, options=options, use_subprocess=True)
        else:
            driver = uc.Chrome( options=options,use_subprocess=True)
        driver.set_window_size(400, 300)
        results = []
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 40)
            show_popup_non_blocking("Automation started. Do not close the browser!\nLooking for the Newest Version",
                                    "System Message", 10)
            tab_xpath = "//li[contains(., 'Previous Versions')]"
            tab = wait.until(EC.element_to_be_clickable((By.XPATH, tab_xpath)))
            driver.execute_script("arguments[0].click();", tab)
            time.sleep(5)

        except Exception as e:
            print(f" > Exception in get_active_session_id: {e}")

        full_html = driver.page_source
        chunks = full_html.split('class="accordion1"')

        for chunk in chunks[1:]:
            v_match = re.search(r'[A-Z]\.\d+\.\d+', chunk)
            v_num = v_match.group(0) if v_match else None
            if v_num:
                raw_os = re.findall(r'Windows\s*(?:11|10|8|7|Server|XP)', chunk, re.I)
                clean_os = sorted(list(set([" ".join(o.split()).strip() for o in raw_os])))
                results.append({"Version": v_num, "OS": clean_os})

    except Exception as e:
        print(f" > Exception in get_active_session_id: {e}")

    try:
        safe_close_driver(driver)
    except Exception as e:
        print(f" > Exception in get_active_session_id: {e}")

    return results

# The download the latest firmware version for the OS from url function
def download_keysight_version(target_version, url, model, download=False, download_path=None, download_defult=None):

    options = uc.ChromeOptions()
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--start-maximized')
    file_name = None

    try:
        chrome_version = get_chrome_major_version()
        if chrome_version:
            driver = uc.Chrome(version_main=chrome_version, options=options, use_subprocess=True)
        else:
            driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_window_size(400, 300)
        driver.get(url)
        WebDriverWait(driver, 40)
        show_popup_non_blocking("Automation started. Do not close the browser!\nLooking for the Newest Version for the OS", "System Message", 10)
        time.sleep(10)

        buttons = driver.find_elements(By.CSS_SELECTOR, "a.cta-download")

        target_btn = None
        target_url = None

        for btn in buttons:
            raw_version = btn.get_attribute("data-version")
            if raw_version and target_version in raw_version:
                path = btn.get_attribute("data-ctadownloadcomppath")
                target_url = f"https://keysight.com{path}"
                target_btn = btn
                break

        if not target_btn:
            print(f"Version {target_version} not found on page.")
            return {"Version": target_version, "Success": False, "Path": None, "File Name": target_version}

        if not download:
            safe_close_driver(driver)
            return {"Version": target_version, "Success": False, "Path": url, "File Name": target_version}

        folder = Path(download_path, model)
        folder.mkdir(parents=True, exist_ok=True)
        if any(f.is_file() and target_version.lower() in f.name.lower() for f in folder.iterdir()):
            print(f"Find the {target_version} in {download_path}//{model} no need to download.")
            safe_close_driver(driver)
            return {"Version": target_version, "Success": True, "Path": download_path, "File Name": target_version}
        else:
            print(f"Need to Download Version {target_version}")

            driver.execute_script("arguments[0].scrollIntoView(true);", target_btn)
            time.sleep(5)

            show_popup_non_blocking("Automation started. Do not close the browser!\nDownloading the Newest Version for the OS", "System Message", 30)
            driver.execute_script("arguments[0].click();", target_btn)
            driver.maximize_window()
            wait = WebDriverWait(driver, 20)
            time.sleep(10)
            wait_for_cloudflare_if_needed(driver, timeout=180)
            form_data = {
                "EmailAddress": "A@A.com",
                "FirstGivenName": "A",
                "LastName": "A",
                "CompanyName": "A",
            }

            checkbox = wait.until(EC.presence_of_element_located((By.NAME,"rememberMe" )))

            if not checkbox.is_selected():
                for name, value in form_data.items():
                    element = wait.until(EC.element_to_be_clickable((By.NAME, name)))
                    human_type_with_mouse(driver, element, value)
                    time.sleep(2)

                print("All fields have been successfully filled in using the injection method!")
                ensure_remember_me_checked(driver, 30)
                time.sleep(5)

            download_btn = wait.until(EC.element_to_be_clickable((By.NAME, "Download")))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});",download_btn)
            time.sleep(5)

            try:
                download_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();",download_btn)

            if check_standard_download(download_btn, download_defult):
                file_name = copy_file_by_name(download_defult, model, download_path, target_version)
                safe_close_driver(driver)

    except Exception as e:
        print(f" > Exception in get_active_session_id: {e}")

    return {"Version": target_version, "Success": True, "Path": download_path, "File Name": file_name}

def ensure_remember_me_checked(driver, timeout=30):

    wait = WebDriverWait(driver, timeout)
    try:
        checkbox = wait.until(EC.presence_of_element_located((By.NAME,"rememberMe")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
        if not checkbox.is_selected():
            try:
                checkbox.click()
            except Exception:
                driver.execute_script("arguments[0].click();", checkbox)

        wait.until(lambda d: d.find_element(By.NAME, "rememberMe").is_selected())

        print(" > Remember me checkbox is selected.")
        return True

    except Exception as e:
        print(f" > Failed to select Remember me: {e}")
        return False


def set_checkbox_state(driver, wait, checkbox_text, checked=True):

    checkbox = wait.until(EC.presence_of_element_located((By.XPATH, f"//label[contains(normalize-space(.), '{checkbox_text}')]/preceding::input[@type='checkbox'][1]")))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", checkbox)
    current = checkbox.is_selected()

    if current != checked:
        try:
            checkbox.click()
        except Exception:
            driver.execute_script(
                "arguments[0].click();",
                checkbox
            )

    wait.until(lambda d: checkbox.is_selected() == checked)

    return checkbox.is_selected()

# The numan typing function - for the software download (to not look like bot)
def human_type_with_mouse(driver, element, text):
    actions = ActionChains(driver)

    actions.move_to_element(element).click().perform()
    time.sleep(random.uniform(0.3, 0.7))

    for char in text:
        actions.send_keys(char).perform()
        time.sleep(random.uniform(0.05, 0.25))

# The popup massages to the user function
def show_popup_non_blocking(message, title, seconds):
    def worker():
        ctypes.windll.user32.MessageBoxTimeoutW(0, message, title, 0x40 | 0x1000, 0, seconds * 1000)
    t = threading.Thread(target=worker)
    t.start()

# The popup massage that is waiting for the user  function - if the download didn't start
def wait_for_user(message, title):
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x0 | 0x40 | 0x1000)

# the check download function - the ss if the download start/end
def check_standard_download(button, downloads_path, timeout=1200):
    trays = 5
    attempt = 1

    while attempt < trays:
        time.sleep(5)
        files = os.listdir(downloads_path)
        if any(f.endswith('.crdownload') for f in files):
            attempt = 5
            break
        else:
            print(f"Clicking on the Download button...({attempt}/{trays})")
            time.sleep(5)
            button.click()
            attempt += 1

    print(f"Monitoring folder: {downloads_path}")
    start_time = time.time()
    no_download = False
    start_download = False

    while time.time() - start_time < timeout:
        time.sleep(20)
        files = os.listdir(downloads_path)
        elapsed_time = int(time.time() - start_time)

        if any(f.endswith('.crdownload') for f in files):
            if hasattr(sys, "stdout") and sys.stdout:
                sys.stdout.write(f"\rStatus: Downloading... ({elapsed_time}s/{timeout})  ")
                sys.stdout.flush()
            time.sleep(2)
            start_download = True
        else:
            no_download = True
            break

        time.sleep(5)

    print("\n")
    folder_files = os.listdir(downloads_path)
    recent_files = [os.path.join(downloads_path, f) for f in folder_files]
    if recent_files:
        latest_file = max(recent_files, key=os.path.getctime)
        if time.time() - os.path.getctime(latest_file) < 540:
            print(f"Success! File found: {os.path.basename(latest_file)}")
            return True

    if no_download and not start_download:
        print("Error: Download didn't started.")
        wait_for_user("Download didn't started!\nSomething went wrong!\nPlease download it manually!"
                      "\nPlease press the OK after download.", "Error")
        print("The user clicked OK, closing now...")
        return False
    elif start_download:
        print("Error: Download timed out.")
        return False
    else:
        print("Error: Something went Wrong!")
        return None

def copy_file_by_name(source_folder, device_model,  destination_folder, contains_text):

    source = Path(source_folder)
    destination = Path(destination_folder, device_model)
    destination.mkdir(parents=True, exist_ok=True)
    files = [f for f in source.iterdir()if f.is_file() and contains_text.lower() in f.name.lower()]

    if not files:
        return None

    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    target = destination / latest_file.name
    shutil.copy2(latest_file, target)

    return str(target)

def safe_close_driver(driver):
    if driver is None:
        return

    user_data_dir = None

    try:
        arguments = getattr(driver.options, "arguments", [])

        for arg in driver.options.arguments:
            if arg.startswith("--user-data-dir="):
                user_data_dir = arg.split("=", 1)[1].strip('"')
                break
    except Exception:
        pass

    try:
        driver.quit()
    except Exception:
        pass

    time.sleep(2)

    if user_data_dir:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmdline_parts = proc.info.get("cmdline") or []
                cmdline = " ".join(cmdline_parts)

                is_chrome = name in (
                    "chrome.exe",
                    "chromedriver.exe",
                )

                belongs_to_profile = (user_data_dir.lower() in cmdline.lower())

                if is_chrome and belongs_to_profile:
                    #print( f" > Killing leftover process "f"{name} PID {proc.pid}")
                    proc.kill()

            except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
            ):
                pass
            except Exception as e:
                print(f" > Process cleanup error: {e}")

        time.sleep(1)

        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception as e:
            print(f" > Failed removing Chrome profile: {e}")


if __name__ == "__main__":

    target_os = "Windows 10"
    target_url_folder = load_configFile("url_path")
    upgrade_path = ['B.06.30', 'C.07.02']
    url = get_urls("E5061B", target_url_folder)

    """all_versions = get_keysight_versions_with_os(url)
    result = get_latest_for_os(all_versions, target_os)
    print(f"Latest Version for {target_os}: {result['Version']}")
    print(f"Download Link: {result['Download']}")"""

    latest = get_latest_version_for_os(target_os, url)
    print(f"The latest version for {target_os} is: {latest}")

    link = download_keysight_version(latest, url, download=True)
    print(f"The firmware {latest} file is in: {link}")

    os._exit(0)


