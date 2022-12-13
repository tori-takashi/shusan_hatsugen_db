from datetime import datetime, timedelta
from time import sleep
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

from config import SID_BEGIN, SID_END, MEETING_TERM

# https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=6637
# 2022年度最初の国会
# https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=6978
# 2022年6月最後の国会


URL_BASE = "https://www.webtv.sangiin.go.jp/webtv/detail.php?sid="

class MeetingInfo:
    def __init__(self, meeting_date, meeting_name: str, meeting_content: str, meeting_duration: timedelta):
        self.meeting_date = meeting_date,
        self.meeting_name = meeting_name,
        self.meeting_content = meeting_content
        self.meeting_duration = meeting_duration


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
        calculated_speaches: list[Speach] = []
        for speaker_num, speach in enumerate(speaches):
            speach_duration = None
            next_speaker_num = speaker_num + 1
            if (next_speaker_num < len(speaches)):
                speach_duration =  speaches[next_speaker_num].time_min - speach.time_min
            else:
                speach_duration = self.info.meeting_duration - speaches[speaker_num].time_min
            calculated_speach = Speach(speach.speaker.name, speach.speaker.attributes, speach_duration)
            calculated_speaches.append(calculated_speach)
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
            self.__meeting_duration = self.__get_meeting_duration()            

            self.__meeting_contents = self.__get_meeting_contents()

            self.__meeting_info = self.__get_meeting_info()
            self.__speaches = self.__get_speaches()

            self.meeting = self.__get_meeting()

    def __get_meeting(self):
        return Meeting(
            self.__meeting_info, self.__speaches)

    def __get_meeting_info(self):
        return MeetingInfo(self.__meeting_date, self.__meeting_name, self.__meeting_contents, self.__meeting_duration)

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

    def __get_detail_contents(self) -> BeautifulSoup | None:
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
            return "".join(description.get_text().split())
        else:
            pprint("description not found")
            return None

    def __get_meeting_date(self):
        time_text = self.__content_summary[0].find(name="dd").get_text()
        date = datetime.strptime(time_text, '%Y年%m月%d日').date()
        return date

    def __get_meeting_name(self):
        return self.__content_summary[1].find(name="dd").get_text()

    def __get_meeting_duration(self):
        duration_text: str = self.__content_summary[2].find(name="dd").get_text()

        hours_r: str = re.search(r'\d+時間', duration_text)
        minutes_r: str = re.search(r'\d+分', duration_text)

        hours = int(hours_r.group().replace('時間', '')) if hours_r else 0
        minutes = int(minutes_r.group().replace('分', '')) if minutes_r else 0

        duration_sec = timedelta(hours=hours, minutes=minutes).seconds
        return round(duration_sec/60)

    def __get_time(self, time_raw):
        href_time_sec = time_raw.replace("#", "")
        href_time_min = float(href_time_sec) / 60
        rounded = round(href_time_min)
        return rounded

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
        for i in range(SID_END - SID_BEGIN + 1):
            url = URL_BASE + str(SID_BEGIN + i)
            meeting_downloader = MeetingDownloader(url)
            if (meeting_downloader.meeting_info_page):
                meeting_info_list.append(meeting_downloader.meeting_info_page)
            #sleep(1)
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
                    "meeting_date": meeting_info_page.meeting.info.meeting_date[0],
                    "meeting_name": "".join(meeting_info_page.meeting.info.meeting_name),
                    "meeting_content": meeting_info_page.meeting.info.meeting_content,
                    "name": speach.speaker.name,
                    "attributes": speach.speaker.attributes,
                    "time_min": speach.time_min
                })
        return meeting_dict_list


class UpperHouseMember:
    def __init__(self, name, name_kana, party):
        self.name = name
        self.name_kana = name_kana
        self.party = party

class UpperHouseMembersPage:
    def __init__(self, upper_house_members_bs):
        self.upper_house_members_bs = upper_house_members_bs
        self.__main_contents = self.upper_house_members_bs.find(name="div", id="ContentsBox")
        self.__members_table = self.__main_contents.find_all(name="table")[1]
        self.__member_rows = self.__members_table.find_all(name="tr")[1:]
        self.members = self.__get_upper_house_members()

    def __get_upper_house_members(self) -> list[UpperHouseMember]:
        members_list = []
        for member_row in self.__member_rows:
            upper_house_member_row_contents = member_row.find_all(name="td")
            name_raw = upper_house_member_row_contents[0].text
            name = "".join(name_raw.split())
            name_kana_raw = upper_house_member_row_contents[1].text
            name_kana = name_kana_raw.replace('\u3000', " ")
            party = upper_house_member_row_contents[2].text

            if ('[' in name):
                current_name, past_name = name.replace("]", "").split('[')
                members_list.append(UpperHouseMember(current_name, name_kana, party))
                members_list.append(UpperHouseMember(past_name, name_kana, party))
            else:
                members_list.append(UpperHouseMember(name, name_kana, party))

        # データが古いので手動で対応
        members_list.append(UpperHouseMember("山崎真之輔", "やまざき しんのすけ", ""))
        members_list.append(UpperHouseMember("宮口治子", "みやぐち はるこ", ""))
        members_list.append(UpperHouseMember("羽田次郎", "はた じろう", ""))
        members_list.append(UpperHouseMember("比嘉奈津美", "ひが なつみ", ""))

        return members_list
        
class UpperHouseMembersDownloader:
    def __init__(self):
        url = "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/"+str(MEETING_TERM)+"/giin.htm"
        upper_house_members_response = requests.get(url)
        upper_house_members_bs = BeautifulSoup(
            upper_house_members_response.content, 'html.parser')
        self.upper_house_members_page = UpperHouseMembersPage(upper_house_members_bs)
        self.upper_house_dict_list = self.__get_upper_house_member_dict_list()
        self.upper_house_members_df = pd.DataFrame(self.upper_house_dict_list)

    def __get_upper_house_member_dict_list(self) -> list[dict]:
        return [{
            "name": member.name,
            "name_kana": member.name_kana,
        } for member in self.upper_house_members_page.members]