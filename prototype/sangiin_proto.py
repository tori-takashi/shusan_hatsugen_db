from datetime import date, timedelta
from time import sleep
from pprint import pprint
import requests
import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd

# https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=6637
# 2022年度最初の国会

URL_BASE = "https://www.webtv.sangiin.go.jp/webtv/detail.php?sid="
#SID_BASE = 6637
SID_BASE = 7037


def get_content_summary(detail_contents):
    return detail_contents.find_all(name="dl", class_="date")


def get_meeting_date(content_summary):
    return content_summary[0].find(name="dd").text


def get_meeting_name(content_summary):
    return content_summary[1].find(name="dd").text


def get_name(speaker_name_attr: str):
    return re.sub("\(.+?\)", "", speaker_name_attr)


def get_speaker_attributes(speaker_name_attr: str):
    attributes_str = re.search(
        "(?<=\().+?(?=\))", speaker_name_attr).group().replace('\u3000', '、')
    return attributes_str.split('、')


meeting_info_dict_list = []

for i in range(50):
    url = URL_BASE + str(SID_BASE + i)
    meeting_page_response = requests.get(url)
    pprint(url + " を取得中")
    if (meeting_page_response.status_code == 200):
        meeting_page_bs = BeautifulSoup(
            meeting_page_response.content, "html.parser")

        detail_contents = meeting_page_bs.find(
            name="div", id="detail-contents-inner")
        if (not detail_contents):
            pprint("content not found")
            continue

        content_summary = get_content_summary(detail_contents)
        meeting_date = get_meeting_date(content_summary)
        meeting_name = get_meeting_name(content_summary)

        description = detail_contents.find(name="span")
        # 厄介なので後回し
        if (description):
            # pprint(description.get_text().split('\u3000'))
            pass
        else:
            pprint("description not found")

        speaker_times_ul = detail_contents.find(name="ul")
        if (speaker_times_ul):
            speaker_times_elm = speaker_times_ul.find_all('li')
            for speaker_time_elm in speaker_times_elm:
                speaker_time = speaker_time_elm.find(name="a")

                speaking_time = int(
                    float(speaker_time.get('href').replace("#", "")))
                speaker_name_attr = speaker_time.text
                speaker_name = get_name(speaker_name_attr)
                speaker_attr = get_speaker_attributes(speaker_name_attr)

                meeting_info_dict_list.append({
                    "meeting_name": meeting_name,
                    "date": meeting_date,
                    "name": speaker_name,
                    "attributes": ",".join(speaker_attr),
                    "time_min": speaking_time / 60,
                })

        else:
            pprint("speaker times elm not found")
    else:
        pprint("not found")
    sleep(1)

meeting_df = pd.DataFrame(meeting_info_dict_list)
meeting_df.to_excel("sangiin.xlsx")
