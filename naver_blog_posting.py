import time
import json
import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC



user_id = ""
user_pw = "!"
LOGIN_URL = "https://nid.naver.com/nidlogin.login?url=https%3A%2F%2Fsection.blog.naver.com%2FBlogHome.naver" 
POST_URL = f"https://blog.naver.com/{user_id}?Redirect=Write" 
IMAGE_PATH = ""
IMAGE_WIDTH = 720



def blog_login(driver):
    print("*** login ***")
    driver.get(LOGIN_URL)
    time.sleep(1)

    driver.execute_script("document.getElementsByName('id')[0].value=\'" + user_id + "\'")
    driver.execute_script("document.getElementsByName('pw')[0].value=\'" + user_pw + "\'")
    driver.find_element(By.XPATH, '//*[@id="log.login"]').click()
    time.sleep(1)


def write_text(driver, text):
    action = ActionChains(driver)
    action.send_keys(text).pause(1).send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
    action.reset_actions()
    print(">> 내용 작성 완료")
    time.sleep(3)


def write_title(driver, text):
    title = driver.find_element(By.CSS_SELECTOR, '.se-placeholder.__se_placeholder.se-fs32')
    action = ActionChains(driver)
    action.move_to_element(title).pause(1).click().send_keys(text + " ").perform()
    action.reset_actions()
    print(">> 제목 작성 완료")
    time.sleep(3)


def get_image_name(url):
    image_name = url.split("/")[-1]
    return image_name


def download_image(url):
    file_path = IMAGE_PATH + get_image_name(url)
    response = requests.get(url)
    
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            file.write(response.content)
        print(f">> 이미지 다운로드 완료: {file_path}")
    else:
        print(">> 이미지 다운로드 실패")


def resize_image(image_path):
    try:
        image = Image.open(image_path)
        original_width, original_height = image.size

        new_height = int((IMAGE_WIDTH / original_width) * original_height)
        resized_image = image.resize((IMAGE_WIDTH, new_height), Image.ANTIALIAS)
        resized_image.save(image_path) 
        print(">> 이미지 리사이즈 완료")
    except Exception as e:
        print(">> 이미지 리사이즈 실패: ", e)
    

def upload_image(driver, url):
    file_name = get_image_name(url)
    file_path = IMAGE_PATH + file_name
    
    download_image(url)
    resize_image(file_path)

    driver.find_element(By.XPATH, '//button[@data-name="image"]').click() # 사진 버튼 클릭해야 input 태그가 생성됨
    file_input = driver.find_element(By.XPATH, '//input[@type="file" and @id="hidden-file"]') # input 태그 찾아서
    driver.execute_script("arguments[0].style.display = 'inline';", file_input) # 화면에 보일 수 있게 display 속성을 보이게 바꾸고
    file_input.send_keys(file_path) # 파일을 보낸다

    # alt 속성이 파일 이름인 img 태그가 생성됐는지 확인, 생성이 됐으면 업로드가 된것임
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//img[@alt="{file_name}"]'))
        )
        print(">> 파일 업로드 완료")
    except Exception as e:
        print(">> 파일 업로드 실패: ", e)


def close_existing_post(driver):
    try:
        cancel = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.se-popup-button.se-popup-button-cancel'))
        )
        cancel.click()
        print(">> 기존 작성 글 닫기")
    except Exception as e:
        print(">> 기존 작성 글 닫기 버튼이 없음")


def write_quote(driver, text):
    button = driver.find_element(By.XPATH, "//button[@class='se-document-toolbar-icon-select-button se-insert-quotation-default-toolbar-button se-text-icon-toolbar-button']")
    driver.execute_script("arguments[0].click();", button)

    action = ActionChains(driver)
    action.send_keys(text).pause(1).send_keys(Keys.ARROW_DOWN).pause(1).send_keys(Keys.ARROW_DOWN).pause(1).send_keys(Keys.ENTER).perform()
    action.reset_actions()
    print(">> 인용구 작성 완료")
    time.sleep(1)


def align(driver):
    button = driver.find_element(By.XPATH, "//button[@data-name='align-drop-down-with-justify']")
    driver.execute_script("arguments[0].click();", button)
    button = driver.find_element(By.XPATH, "//button[@data-value='center']")
    driver.execute_script("arguments[0].click();", button)


def choose_category(driver):
    # 카테고리 선택 (추후에 원하는 카테고리 입력받아서 그걸로 선택)
    button = driver.find_element(By.XPATH, "//button[@aria-label='카테고리 목록 버튼' and @aria-expanded='false']")
    driver.execute_script("arguments[0].click();", button)
    label = driver.find_element(By.XPATH, "//label[@for='6_게시판2']")
    driver.execute_script("arguments[0].click();", label)


def complete_writing(driver):
    button = driver.find_element(By.XPATH, '//button[@class="publish_btn__Y5mLP"]')
    driver.execute_script("arguments[0].click();", button)

    choose_category(driver)
    
    button = driver.find_element(By.XPATH, '//button[@class="confirm_btn__Dv9du"]')
    driver.execute_script("arguments[0].click();", button)
    print(">> 게시글 작성 완료")
    time.sleep(3)


def blog_post(driver):
    print("*** blog_post ***")
    driver.get(POST_URL)
    driver.implicitly_wait(10)

    iframe = driver.find_element(By.XPATH, '//*[@id="mainFrame"]')
    driver.switch_to.frame(iframe)
    print(">> 프레임 전환")
    time.sleep(10)

    close_existing_post(driver)
    
    with open("post.json") as f:
        json_data = json.load(f)

    align(driver)

    write_title(driver, json_data["title"])

    for i, content in enumerate(json_data["contents"]):
        content_type = content["type"]
        content_data = content["data"]

        if content_type == "text":
            if i == 0:
                print(">> 본문 선택")
                content_element = driver.find_element(By.CSS_SELECTOR, '.se-component.se-text.se-l-default')
                content_element.click()

            write_text(driver, content_data)
        elif content_type == "image":
            upload_image(driver, content_data)
        elif content_type == "quote":
            write_quote(driver, content_data)
        else:
            print("Invalid content type:", content_type)

    complete_writing(driver)
    


if __name__ == '__main__':
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--disable-popup-blocking")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    blog_login(driver)
    blog_post(driver)

    driver.close()