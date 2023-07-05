import re
import time
import requests
from emoji import core
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains


BLOG_DOMAIN = "https://blog.naver.com/"
COMMENT = ""
IMAGE_PATH = ""


def scroll_down_to_bottom(driver):
    while True:
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    

def remove_emojis(s):
    return core.replace_emoji(s, replace="")


def get_blog_contents(url):
    try:
        response = requests.get(url)
        frame_soup = BeautifulSoup(response.content, 'html.parser')

        content = frame_soup.select('div.se-text p.se-text-paragraph')
        content_text = ''
        for item in content:
            text = item.select_one('span').get_text()
            content_text += (text + " ")
        content_text = re.sub(r'\s+', ' ', content_text)

        content_text = remove_emojis(content_text) # 이모지 제거
        url_pattern = r"(http|https)?:\/\/[a-zA-Z0-9-\.]+\.[a-z]{2,}(\S*)?|www\.[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|([a-zA-Z0-9-]+\.)?naver.com(\S*)?"
        content_text = re.sub(url_pattern, "", content_text) # URL 제거
        content_text = re.sub(r"\u200C|\u200b", "", content_text) # 제로 너비 공간 제거
        content_text = ' '.join(content_text.split()) # 공백 2개 이상 인 것들, 1개로 치환
        content_text = content_text.replace("'", '"') # 작은 따옴표 -> 큰 따옴표로 변환
    except Exception as e :
        print(e)


def post_comment(driver, url):
    url = url.replace("/PostView.naver?", "/CommentList.naver?")
    url = url.replace("&redirect=Dlog&widgetTypeCall=true&directAccess=false", "")
    print("post_blog_url:", url)

    driver.get(url)
    time.sleep(2)

    # 댓글 작성할 div 요소 선택
    comment_box = driver.find_element(By.CLASS_NAME, "u_cbox_write_area")

    # 댓글 입력
    actions = ActionChains(driver)
    actions.move_to_element(comment_box).click().send_keys(COMMENT).perform()
    actions.reset_actions()
    time.sleep(2)

    # 비밀 댓글 선택
    secret = driver.find_element(By.CLASS_NAME, "u_cbox_secret_tag")
    actions = ActionChains(driver)
    actions.move_to_element(secret).click().send_keys(Keys.ENTER).perform()
    actions.reset_actions()
    time.sleep(2)

    # 이미지 업로드
    input_image = driver.find_element(By.CLASS_NAME, "u-cbox-browse-file-input")
    input_image.send_keys(IMAGE_PATH)
    time.sleep(3)

    # 댓글 작성 완료
    comment_submit_btn = driver.find_element(By.CLASS_NAME, "u_cbox_btn_upload")
    actions = ActionChains(driver)
    actions.move_to_element(comment_submit_btn).click().send_keys(Keys.ENTER).perform()
    actions.reset_actions()

    time.sleep(3)
    print(">> 댓글 작성 완료")

    return True



if __name__ == '__main__':
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    chrome_driver = "~/chromedriver.exe" 
    driver = webdriver.Chrome(options=chrome_options)


    for i in range(1, 5):
        URL = f'https://search.naver.com/search.naver?query=제주도자전거종주%2B{i}&nso=&where=view&sm=tab_nmr&mode=normal'
        print(f"<< {i}일차: {URL} >>")

        driver.get(URL)
        time.sleep(2)
        scroll_down_to_bottom(driver)
        time.sleep(2)

        a = driver.find_elements(By.CSS_SELECTOR, "#main_pack > section > div > div._list > panel-list > div > more-contents > div > ul > li > div.total_wrap.api_ani_send > div > a")
        href_list = [item.get_attribute('href') for item in a]

        for j, href in enumerate(href_list):
            print(f"{j+1}번째 href: {href}")
            if not href.startswith(BLOG_DOMAIN):
                print("블로그가 아닙니다\n")
                continue

            response = requests.get(href)
            soup = BeautifulSoup(response.text, 'html.parser')
            frame = soup.find('iframe', id="mainFrame")
            frameaddr = BLOG_DOMAIN + frame['src']
            frameaddr = frameaddr.replace("blog.naver.com//", "m.blog.naver.com/")
            print(f"frame_url: {frameaddr}")

            get_blog_contents(frameaddr)
            post_result = post_comment(driver, frameaddr)
            print()
        print()
            
