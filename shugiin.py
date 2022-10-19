from datetime import date, timedelta
from time import sleep
from pprint import pprint
import requests
import bs4
from bs4 import BeautifulSoup
import re

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
        return details_downloader.get_meeting_details()


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


class Topic:
    def __init__(self, topic_elm: bs4.element.Tag):
        self.title = self.__get_title(topic_elm)

    def __get_title(self, topic_elm):
        return topic_elm.text


class Speaker:
    def __init__(self, speaker_elm: bs4.element.Tag):
        self.name = self.__get_name(speaker_elm)

    def __get_name(self, speaker_elm):
        return speaker_elm.text


class MeetingDetails:
    def __init__(self, topics: list[Topic], speakers: list[Speaker]):
        self.topics = topics
        self.speakers = speakers


class MeetingDetailsDownloader:
    def __init__(self, meeting_search_result: MeetingSearchResult):
        self.meeting_details_page_data = self.__get_meeting_details_page(
            meeting_search_result.meeting_detail_url)

    def __get_meeting_details_page(self, meeting_detail_url: str) -> BeautifulSoup:
        meeting_details_page_response = requests.get(meeting_detail_url)
        return BeautifulSoup(meeting_details_page_response.content, "html.parser")

    def get_meeting_details(self) -> MeetingDetails:
        topics_elm = self.meeting_details_page_data.select('td[width="595"]')
        topics = [Topic(topic_elm) for topic_elm in topics_elm]
        speakers_elm = self.meeting_details_page_data.select(
            'td[width="380"] a')
        speakers = [Speaker(speaker_elm) for speaker_elm in speakers_elm]
        return MeetingDetails(topics, speakers)


class MeetingInfo:
    def __init__(self, meeting_summary: MeetingSearchResult, meeting_details: MeetingDetails):
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
            "topics": [topic.title for topic in self.meeting_details.topics],
            "speakers": {
                "text": [speaker.name for speaker in self.meeting_details.speakers]
            }
        }


class MeetingDownloader:
    def __init__(self, meeting_date):
        search_results_downloader = MeetingSearchDownloader(meeting_date)
        meeting_search_results = search_results_downloader.get_meeting_search_results()
        self.meetings = [MeetingInfo(meeting_summary, meeting_summary.get_meeting_details()).meeting_info_dict
                         for meeting_summary in meeting_search_results]


meeting_start_date = date(2022, 10, 1)
meetings = {}
for i in range(20):
    meeting_date = meeting_start_date + timedelta(days=i)
    meetings[meeting_date] = MeetingDownloader(meeting_date).meetings
    print(f"{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日の情報を取得中")
    sleep(1)

pprint(meetings)
