import re
import csv
import requests
from bs4 import BeautifulSoup
from emoji import core


KEYWORD = '비엔나 커피'
URL = f'https://search.naver.com/search.naver?query={KEYWORD}&nso=&where=view&sm=tab_nmr&mode=normal'
BLOG_DOMAIN = "https://blog.naver.com/"


def remove_emojis(s):
    return core.replace_emoji(s, replace="")


def get_content_text(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    content = soup.find('div', 'se-main-container')
    if content is None:
        content = soup.select_one('#postViewArea')
    if content is None:
        content = soup.select_one('div.se_component_wrap.sect_dsc.__se_component_area > div.se_component.se_paragraph.default > div > div > div > div > div > p')

    if content:
        content_text = content.get_text(strip=True)
        content_text = remove_emojis(content_text)
        url_pattern = r"(http|https)?:\/\/[a-zA-Z0-9-\.]+\.[a-z]{2,}(\S*)?|www\.[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|[a-zA-Z0-9-]+\.[a-z]{2,}(\S*)?|([a-zA-Z0-9-]+\.)?naver.com(\S*)?"
        content_text = re.sub(url_pattern, "", content_text)
        content_text = re.sub(r"\u200C|\u200b", "", content_text)
        content_text = ' '.join(content_text.split())
        return content_text

    return None


try:
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    li = soup.select('#main_pack > section > div > div._list > panel-list > div > more-contents > div > ul > li')

    with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['idx', 'content_text'])

        for idx, item in enumerate(li):
            a = item.select_one('div.total_wrap.api_ani_send > div > a')
            href = a.get('href')
            if not href.startswith(BLOG_DOMAIN):
                continue

            frameaddr = BLOG_DOMAIN + BeautifulSoup(requests.get(href).text, 'html.parser').find('iframe', id="mainFrame")['src']
            print(frameaddr)

            content_text = get_content_text(frameaddr)
            if content_text:
                print(content_text)
                print()

                writer.writerow([idx, content_text])

except requests.exceptions.RequestException as e:
    print(f"An error occurred during the request: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
