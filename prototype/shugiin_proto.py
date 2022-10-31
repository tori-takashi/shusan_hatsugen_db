from datetime import date, timedelta
from time import sleep
from pprint import pprint
import requests
import bs4
from bs4 import BeautifulSoup
import re
import pandas as pd

# https://www.shugiintv.go.jp/jp/index.php?ex=VL&u_day=20210825
# この中に日毎の本会議・委員会のリンクが入っているのでそれをスクレイピングする

URL_BASE = "https://www.shugiintv.go.jp/jp/"
PARAM_BASE = "ex=VL"


class MeetingSearchResult:
    def __init__(self, result_elm: bs4.element.Tag):
        self.meeting_name = self.__get_meeting_name(result_elm)
        self.meeting_detail_url = self.__get_meeting_detail_url(result_elm)

    def __get_meeting_name(self, result_elm) -> str:
        return result_elm.text

    def __get_meeting_detail_url(self, result_elm) -> str:
        url_filter = "\'.*?\'"
        href = result_elm.get('href')
        return URL_BASE + re.sub("'", "", re.search(url_filter, href).group())

    def get_meeting_details(self):
        details_downloader = MeetingDetailsDownloader(self)
        return details_downloader.meeting_details.get_meeting_details()


class MeetingSearchDownloader:
    def __init__(self, meeting_date):
        self.meetings_search_page_data = self.__get_meetings_by_date(
            meeting_date)

    def __get_meetings_by_date(self, date: date) -> BeautifulSoup:
        return self.__get_meetings_page_by_ymd(date.year, date.month, date.day)

    def __get_meetings_page_by_ymd(self, year: int, month: int, day: int) -> BeautifulSoup:
        year_str = str(year)
        month_str = str(month).zfill(2)
        day_str = str(day).zfill(2)
        meetings_page_response = requests.get(
            URL_BASE + "index.php?" + PARAM_BASE + "&u_day=" + year_str + month_str + day_str)
        return BeautifulSoup(meetings_page_response.content, "html.parser")

    def get_meeting_search_results(self) -> list[MeetingSearchResult]:
        search_results = self.meetings_search_page_data.select(
            'td[class="s14_24"] a')
        return [MeetingSearchResult(result_elm) for result_elm in search_results]


class SpeakerTime:
    def __init__(self, speaker_time: dict):
        self.name = self.__get_name(speaker_time["name"])
        self.attributes = self.__get_speaker_attributes(speaker_time["name"])
        self.speak_time = self.__get_speak_time(speaker_time["time"])

    def __get_name(self, speaker_name_attr: str):
        return re.sub("\(.+?\)", "", speaker_name_attr)

    def __get_speaker_attributes(self, speaker_name_attr: str):
        attributes_str = re.search(
            "(?<=\().+?(?=\))", speaker_name_attr).group()
        return attributes_str.split('・')

    def __get_speak_time(self, speak_time: str):
        hour_min_text_list = speak_time.split()
        # 表記はn時間 n分とn分だけなので
        if (len(hour_min_text_list) > 1):
            hours_text = hour_min_text_list[0]
            hours = int(re.sub(r"\D", "", hours_text))
            min_text = hour_min_text_list[1]
            minutes = int(re.sub(r"\D", "", min_text))
            return timedelta(hours=hours, minutes=minutes)
        else:
            min_text = hour_min_text_list[0]
            minutes = int(re.sub(r"\D", "", min_text))
            return timedelta(minutes=minutes)


class MeetingDetails:
    def __init__(self, topics: list[str], speaker_time: list[SpeakerTime]):
        self.topics = topics
        self.speaker_time = speaker_time


class MeetingDetailsPage:
    def __init__(self, meeting_details_page_data: BeautifulSoup):
        self.meeting_details_page_data = meeting_details_page_data
        self.tables = self.__get_tables()
        self.topics_table = self.__get_topics_table()
        self.speakers_table = self.__get_speakers_list_table()
        self.speakers_time_table_with_responder_ministers = self.__get_speaker_time_list_table()

        self.rows_topics = self.__get_rows(self.topics_table)
        self.topics_list = self.__parse_topic_rows()

        self.rows_speakers_time_table_with_responder_ministers = self.__get_rows(
            self.speakers_time_table_with_responder_ministers)
        self.speaker_time_list = self.__parse_speaker_time_table_rows()

    def __get_tables(self):
        tables = self.meeting_details_page_data.select(
            'div#library2 table')
        return tables

    def __get_topics_table(self):
        return self.tables[0]

    def __get_speakers_list_table(self):
        return self.tables[1]

    def __get_speaker_time_list_table(self):
        speaker_time_with_responder_ministers = self.tables[2]
        return speaker_time_with_responder_ministers

    def __get_rows(self, table):
        rows = table.select('tr')
        return rows

    def __parse_topic_rows(self):
        title_eliminated = self.rows_topics[1:-1]
        return [topic_row.text.strip() for topic_row in title_eliminated]

    def __get_responder_header_tr(self):
        responders_header_elm = self.speakers_time_table_with_responder_ministers.find(
            text="答弁者等")
        if (responders_header_elm):
            return responders_header_elm.parent.parent

    def __get_ministers_header_tr(self):
        ministers_header_elm = self.speakers_time_table_with_responder_ministers.find(
            text="大臣等（建制順）：")
        if ministers_header_elm:
            return ministers_header_elm.parent.parent.parent

    def __parse_speaker_time_table_rows(self):
        title_eliminated = self.rows_speakers_time_table_with_responder_ministers[1:]

        ministers_header_elm = self.__get_ministers_header_tr()
        responders_header_elm = self.__get_responder_header_tr()

        if (ministers_header_elm):
            minister_header_index = title_eliminated.index(
                ministers_header_elm)
            title_eliminated = title_eliminated[:minister_header_index]

        if (responders_header_elm):
            responder_header_index = title_eliminated.index(
                responders_header_elm)
            title_eliminated = title_eliminated[:responder_header_index]

        if (len(title_eliminated) > 1):
            title_eliminated = title_eliminated[:-1]

        speakers_list = [
            {
                "name": speaker_time.select_one('td[width="380"]').text.strip(),
                "start_at": speaker_time.select('td[width="100"]')[0].text.strip(),
                "time": speaker_time.select('td[width="100"]')[1].text.strip()
            } for speaker_time in title_eliminated]

        return speakers_list

    def get_meeting_details(self) -> MeetingDetails:
        speaker_times = [SpeakerTime(speaker_time_dict)
                         for speaker_time_dict in self.speaker_time_list]
        return MeetingDetails(self.topics_list, speaker_times)


class MeetingDetailsDownloader:
    def __init__(self, meeting_search_result: MeetingSearchResult):
        self.__meeting_details_page_data = self.__get_meeting_details_page(
            meeting_search_result.meeting_detail_url)
        self.meeting_details = MeetingDetailsPage(
            self.__meeting_details_page_data)

    def __get_meeting_details_page(self, meeting_detail_url: str) -> BeautifulSoup:
        meeting_details_page_response = requests.get(meeting_detail_url)
        return BeautifulSoup(meeting_details_page_response.content, "html.parser")


class MeetingInfo:
    def __init__(self, meeting_date: date, meeting_summary: MeetingSearchResult, meeting_details: MeetingDetails):
        self.meeting_date = meeting_date
        self.meeting_summary = meeting_summary
        self.meeting_details = meeting_details
        self.meeting_info_dict = {
            "meeting_summary": self.summary_dict(),
            "meeting_details": self.details_dict()
        }

    def summary_dict(self):
        return {
            "meeting_name": self.meeting_summary.meeting_name,
            "meeting_detail_url": self.meeting_summary.meeting_detail_url
        }

    def details_dict(self):
        return {
            "topics": self.meeting_details.topics,
            "speakers": [{
                "name": speaker_time.name,
                "attributes": speaker_time.attributes,
                "time": str(int(speaker_time.speak_time.seconds / 60)) + "分"
            } for speaker_time in self.meeting_details.speaker_time]
        }

    def to_row_dict(self):
        info_dict_list = []
        for speaker_time in self.meeting_details.speaker_time:
            row = {
                "meeting_name": self.meeting_summary.meeting_name,
                "date": self.meeting_date,
                "name": speaker_time.name,
                "attributes": ", ".join(speaker_time.attributes),
                "time_min": int(speaker_time.speak_time.seconds / 60),
                "topics": ",".join(self.meeting_details.topics)
            }
            info_dict_list.append(row)
        return info_dict_list


class MeetingDownloader:
    def __init__(self, meeting_date):
        search_results_downloader = MeetingSearchDownloader(meeting_date)
        meeting_search_results = search_results_downloader.get_meeting_search_results()
        self.meetings: list[MeetingInfo] = [MeetingInfo(meeting_date, meeting_summary, meeting_summary.get_meeting_details())
                                            for meeting_summary in meeting_search_results]


meeting_start_date = date(2022, 10, 13)
meetings = {}
meetings_row_dict_list = []
for i in range(1):
    meeting_date = meeting_start_date + timedelta(days=i)
    print(f"{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日の情報を取得中")
    meeting_info = MeetingDownloader(meeting_date).meetings
    pprint(meeting_info)

    meetings_row_dicts = [meeting.to_row_dict() for meeting in meeting_info]
    pprint(meetings_row_dicts)

    meetings[meeting_date] = meeting_info
    meetings_row_dict_list.extend(meetings_row_dicts)
    sleep(1)

pprint(meetings_row_dict_list)
