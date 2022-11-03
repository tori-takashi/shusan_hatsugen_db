from datetime import date, timedelta
from time import sleep
from pprint import pprint
from turtle import down
import requests
import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd

# https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=6637
# 2022年度最初の国会
# https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=6978
# 2022年6月最後の国会


URL_BASE = "https://www.webtv.sangiin.go.jp/webtv/detail.php?sid="
SID_BEGIN = 6637
SID_END = 6639


class MeetingInfo:
    def __init__(self, meeting_date, meeting_name: str, meeting_content: str):
        self.meeting_date = meeting_date,
        self.meeting_name = meeting_name,
        self.meeting_content = meeting_content


class Speach:
    def __init__(self, name: str, attributes: list[str], time_min: int):
        self.speaker = Speaker(name, attributes)
        self.time_min = time_min


class Speaker:
    def __init__(self, name: str, attriubutes: list[str]):
        self.name = name
        self.attributes = attriubutes


class Meeting:
    def __init__(self, meeting_info: MeetingInfo, speaches: list[Speach]):
        self.info = meeting_info
        self.speaches = self.calculate_speaking_time(speaches)

    def calculate_speaking_time(self, speaches: list[Speach]) -> list[Speach]:
        calculated_speaches = []
        for speach in speaches:
            if calculated_speaches:
                speach_duration = speach.time_min - \
                    calculated_speaches[-1].time_min
                calculated_speaches.append(
                    Speach(speach.speaker.name, speach.speaker.attributes, speach_duration))
            else:
                calculated_speaches.append(speach)
        return calculated_speaches


class MeetingInfoPage:
    def __init__(self, url: str, meeting_page_bs: BeautifulSoup):
        self.url = url
        self.meeting_page_bs = meeting_page_bs
        self.__detail_contents = self.__get_detail_contents()
        self.has_contents = self.__detail_contents is not None
        if (self.__detail_contents):
            self.__content_summary = self.__get_content_summary()
            self.__meeting_date = self.__get_meeting_date()
            self.__meeting_name = self.__get_meeting_name()
            self.__meeting_contents = self.__get_meeting_contents()

            self.__meeting_info = self.__get_meeting_info()
            self.__speaches = self.__get_speaches()

            self.meeting = self.__get_meeting()

    def __get_meeting(self):
        return Meeting(
            self.__meeting_info, self.__speaches)

    def __get_meeting_info(self):
        return MeetingInfo(self.__meeting_date, self.__meeting_name, self.__meeting_contents)

    def __get_speaches(self) -> list[Speach]:
        speaches_list = []
        speaker_times_ul = self.__detail_contents.find(name="ul")
        if (speaker_times_ul):
            speaker_times_elm = speaker_times_ul.find_all('li')
            for speaker_time_elm in speaker_times_elm:
                speaker_time = speaker_time_elm.find(name="a")
                speaches_list.append(self.__generate_speach(speaker_time))
        else:
            pprint("speaker times elm not found")
        return speaches_list

    def __generate_speach(self, speaker_time: BeautifulSoup):
        time_raw = speaker_time.get('href')
        speaker_name_attr_raw = speaker_time.text

        speaking_time = self.__get_time(time_raw)
        name = self.__get_name(speaker_name_attr_raw)
        attributes = self.__get_speaker_attributes(
            speaker_name_attr_raw)

        return Speach(name, attributes, speaking_time)

    def __get_detail_contents(self):
        detail_contents = self.meeting_page_bs.find(
            name="div", id="detail-contents-inner")
        if (detail_contents):
            return detail_contents
        else:
            pprint("content not found")
            return None

    def __get_content_summary(self):
        return self.__detail_contents.find_all(name="dl", class_="date")

    def __get_meeting_contents(self):
        description = self.__detail_contents.find(name="span")
        if (description):
            # pprint(description.get_text().split('\u3000'))
            return "".join(description.get_text().split())
        else:
            pprint("description not found")
            return None

    def __get_meeting_date(self):
        return self.__content_summary[0].find(name="dd").get_text().replace("年", "-").replace("月", "-").replace("日", "")

    def __get_meeting_name(self):
        return self.__content_summary[1].find(name="dd").get_text()

    def __get_time(self, time_raw):
        return round(float(time_raw.replace("#", ""))/60)

    def __get_name(self, speaker_name_attr: str):
        return re.sub("\(.+?\)", "", speaker_name_attr)

    def __get_speaker_attributes(self, speaker_name_attr: str):
        attributes_str = re.search(
            "(?<=\().+?(?=\))", speaker_name_attr).group().replace('\u3000', '、')
        return ", ".join(attributes_str.split('、'))


class MeetingDownloader:
    def __init__(self, url: str):
        self.url = url
        self.__meeting_page_response = requests.get(url)
        self.meeting_info_page = self.__get_meeting_info_page()

    def __get_meeting_info_page(self):
        pprint(self.url + " を取得中")
        if (self.__meeting_page_response.status_code == 200):
            meeting_page_bs = BeautifulSoup(
                self.__meeting_page_response.content, "html.parser")
            meeting_info_page = MeetingInfoPage(self.url, meeting_page_bs)
            if (meeting_info_page.has_contents):
                return meeting_info_page
            else:
                pprint("ページコンテンツが見つかりませんでした。")
        else:
            pprint("ページが見つかりませんでした。")


class MeetingsDownloader:
    def __init__(self):
        self.meeting_info_page_list = self.__get_meeting_info_page()
        self.meeting_info_list_dict = self.__get_meeting_info_dicts()
        self.meeting_dict_list = self.__get_meeting_dict_list()
        self.meetings_df = pd.DataFrame(self.meeting_dict_list)

    def __get_meeting_info_page(self) -> list[MeetingInfoPage]:
        meeting_info_list = []
        for i in range(SID_END - SID_BEGIN):
            pprint(i)
            url = URL_BASE + str(SID_BEGIN + i)
            meeting_downloader = MeetingDownloader(url)
            if (meeting_downloader.meeting_info_page):
                meeting_info_list.append(meeting_downloader.meeting_info_page)
            sleep(1)
        return meeting_info_list

    def __get_meeting_info_dicts(self) -> list[dict]:
        return [{
            "meeting_name": meeting_info_page.meeting.info.meeting_name,
            "meeting_date": meeting_info_page.meeting.info.meeting_date,
            "meeting_content": meeting_info_page.meeting.info.meeting_content,
            "speaches": [{
                "name": speach.speaker.name,
                "attributes": speach.speaker.attributes,
                "time_min": speach.time_min
            } for speach in meeting_info_page.meeting.speaches]
        } for meeting_info_page in self.meeting_info_page_list]

    def __get_meeting_dict_list(self) -> list[dict]:
        meeting_dict_list = []
        for meeting_info_page in self.meeting_info_page_list:
            for speach in meeting_info_page.meeting.speaches:
                meeting_dict_list.append({
                    "meeting_date": "".join(meeting_info_page.meeting.info.meeting_date),
                    "meeting_name": "".join(meeting_info_page.meeting.info.meeting_name),
                    "meeting_content": meeting_info_page.meeting.info.meeting_content,
                    "name": speach.speaker.name,
                    "attributes": speach.speaker.attributes,
                    "time_min": speach.time_min
                })
        return meeting_dict_list


downloader = MeetingsDownloader()
meetings_df = downloader.meetings_df
pprint(meetings_df)
