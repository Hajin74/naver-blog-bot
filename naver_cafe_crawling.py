import re
import time
import urllib.parse
from emoji import core
from utils.database import *
from bs4 import BeautifulSoup
from selenium import webdriver
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


user_id = ''
user_pw = ''
LOGIN_URL = ''
BOARD_URL = ''
SPECIFIC_CATE_URL = ''


def remove_emojis(s):
    return core.replace_emoji(s, replace="")


def preprocess_data(data):
    data = remove_emojis(data)
    url_pattern = r"(http|https)?:\/\/[a-zA-Z0-9-\.]+\.[a-z]{2,}(\S*)?|www\.[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|([a-zA-Z0-9-]+\.)?naver.com(\S*)?"
    data = re.sub(url_pattern, "", data) # URL 제거
    data = re.sub(r"\u200C|\u200b", "", data) # 제로 너비 공간 제거
    data = ' '.join(data.split()) # 공백 2개 이상 인 것들, 1개로 치환

    return data


def scroll_down_to_bottom(driver):
    while True:
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


# 추가할 게시글의 제목을 검사하여 1시간 이내에 동일한 제목이 있는지 확인하고, 있을 경우 삽입을 중단 (중복 방지)
def check_duplicate_title_within_one_hour(title):
    one_hour_ago = datetime.now() - timedelta(hours=1)
    formatted_time = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")
    sql = f"SELECT * FROM `cafes` WHERE `title` LIKE '{title}' AND `created_at` >= '{formatted_time}'"
    result = query(DB, sql)
    return result


def check_duplicate_post(post_id):
    sql = f"SELECT * FROM `cafes` WHERE `cafekey` = {post_id}"
    return query(DB, sql)


def login(driver):
    print("*** login ***")
    driver.get(LOGIN_URL)
    time.sleep(1)

    driver.execute_script("document.getElementsByName('id')[0].value=\'" + user_id + "\'")
    driver.execute_script("document.getElementsByName('pw')[0].value=\'" + user_pw + "\'")
    driver.find_element(By.XPATH, '//*[@id="log.login"]').click()
    driver.find_element(By.XPATH, '//*[@id="new.save"]').click()
    time.sleep(1)



# 특정 카테고리 게시글 조회수 업데이트 하기
def update_read_count(driver):
    print("*** update_read_count ***")
    driver.get(SPECIFIC_CATE_URL) 

    scroll_down_to_bottom(driver)

    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    li = list(map(str, soup.select('li.board_box')))[::-1]
    print("게시물 개수: ", len(li))

    for li_item in li:
        soup = BeautifulSoup(li_item, 'html.parser')
        class_name = soup.find('li')['class']   # class="board_box adtype_infinity" 인 것을 패스하기 위함
        if len(class_name) > 1: 
            continue
        a_tag = soup.find('a', class_='txt_area')   # 게시물 목록에서 게시글 본문 링크를 받아옴
        href_value = a_tag['href']

        try:
            driver.get(href_value)
            time.sleep(3)
            print("url: ", href_value)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            read_count_element = soup.select_one('#ct > div.post_title > div.user_wrap > div:nth-child(3) > span.no.font_l')
            read_count = read_count_element.get_text().strip()
            read_count = int(read_count.split(' ')[1].replace(',', ''))
            print("조회 수: ", read_count)

            parsed_link = urllib.parse.urlparse(str(href_value))
            query_params = urllib.parse.parse_qs(parsed_link.query)
            post_id = query_params.get("articleid")[0]

            sql = f"UPDATE cafes SET `read_count` = {read_count} WHERE `cafekey` = {post_id}"
            query(DB, sql)
            print(sql)
            print()

        except Exception as e:
            print(e)
            continue


def get_comments_count(data):
    comment_count = 0

    comments = data['comments']
    comment_count += len(comments)

    for comment in comments:
        replies = comment.get('reply', [])
        comment_count += len(replies)

    return comment_count


def get_comments_url(url):
    new_url = url.replace("ArticleRead.nhn?clubid=1000&articleid=", "ca-fe/web/cafes/1000/articles/")
    new_url = new_url.replace("&boardtype=L", "/comments?boardtype=L")
    return new_url


def get_cafe_content(driver):
    print("*** get_cafe_content ***")
    driver.get(BOARD_URL) 
    scroll_down_to_bottom(driver)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    li = list(map(str, soup.select('li.board_box')))[::-1]
    print("전체글 게시물 개수: ", len(li))


    for i, li_item in enumerate(li):
        soup = BeautifulSoup(li_item, 'html.parser')

        class_adtype_infinity = soup.find('li')['class']   # class="board_box adtype_infinity" 인 것을 패스하기 위함
        if len(class_adtype_infinity) > 1: 
            continue
        a_tag = soup.find('a', class_='txt_area')   # 게시물 목록에서 게시글 본문 링크를 받아옴
        href_value = a_tag['href']

        
        # 중복된 게시글 방지하기 위함
        parsed_link = urllib.parse.urlparse(str(href_value))
        query_params = urllib.parse.parse_qs(parsed_link.query)
        post_id = query_params.get("articleid")[0]
        result = check_duplicate_post(post_id)

        if len(result) > 0:
            print("url: ", href_value)
            print("이미 존재하는 게시글입니다\n")
            continue
        
        try:
            driver.get(href_value)
            time.sleep(3)
            print("url: ", href_value)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            title_element = soup.select_one('#ct > div.post_title > div.title_area > h2.tit')
            content_element = soup.select_one('#postContent > div.content')
            writer_element = soup.select_one('#ct > div.post_title > div.user_wrap > div:nth-child(2) > a.nick > span > span')
            category_element = soup.select_one('#ct > div.post_title > div.tit_menu > a.border_name > span')
            read_count_element = soup.select_one('#ct > div.post_title > div.user_wrap > div:nth-child(3) > span.no.font_l')

            if title_element is None:
                print(i, "번째: One or more elements not found. Skipping this page.\n")
                time.sleep(1)
                continue

            title = preprocess_data(title_element.get_text())
            content= preprocess_data(content_element.get_text())
            writer = preprocess_data(writer_element.get_text())
            category = preprocess_data(category_element.get_text())
            read_count = read_count_element.get_text().strip()
            read_count = int(read_count.split(' ')[1].replace(',', ''))

            result = check_duplicate_title_within_one_hour(title)
            if len(result) > 0:
                print("1시간 이내에 작성되어진 적이 있는 게시글입니다")
                continue
            else:
                print("새로운 게시글입니다.")


            comments_url = get_comments_url(href_value)     # 전체 댓글 볼 수 있는 페이지로 이동
            driver.get(comments_url)
            time.sleep(3)
            print("comments_url: ", comments_url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            comment = list(map(str, soup.select('#app > div > div > div.CommonComment.talk_comment_wrap > div.TownCommentComponent > div > ul > li')))
            comment_list = []
            commenter = None

            for comment_item in comment:
                comment_item_soup = BeautifulSoup(comment_item, 'html.parser')
                li_tag = comment_item_soup.find('li')
                reply_tag = li_tag.get('class')

                temp = {}
                temp["commenter"] = comment_item_soup.select_one('span.ellip').text
                temp["content"] = comment_item_soup.select_one('p.txt').text

                if len(reply_tag) > 0:
                    result = [item for item in comment_list if item['commenter'] == commenter]
                    if 'reply' in result[-1]:
                        result[-1]['reply'].append(temp)
                    else:
                        result[-1]['reply'] = [temp]
                else:
                    commenter = temp["commenter"]
                    comment_list.append(temp)
            comment_dict = {"comments" : comment_list}
            comments_count = get_comments_count(comment_dict)

            text = title + " " + content
            specific_cafe = category == "정보방"
            
            try:
                sql = f"INSERT INTO cafes (`cafedomain`, `title`, `contents`, `category`, `username`, `comments`, `cafekey`, `cafe_name`, `comments_count`, `read_count`) VALUES ('{href_value}', '{title}', '{content}', '{category}', '{writer}', \"{comment_dict}\", {post_id}, {comments_count}, {read_count})"
                print(sql)
                query(DB, sql)
                print(">> " + str(i) + "번째 데이터 삽입 성공")
            except Exception as e:
                print(">> 데이터 삽입 실패:", str(e))
            finally:
                print()
        
        except Exception as e:
            print(">> ", i, "번째 게시글: ", str(e) + "\n")
            continue


if __name__ == '__main__':
    while True:
        try:
            DB = create_db_connection()
            DB.ping(reconnect=True)

            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            chrome_driver = "~/chromedriver_win32/chromedriver.exe"
            driver = webdriver.Chrome(options=chrome_options)
        
            get_cafe_content(driver)
            update_read_count(driver)
        except Exception as e:
            print(e)
        finally:
            DB.close()
        
        