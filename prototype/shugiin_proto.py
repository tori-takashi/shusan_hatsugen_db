from datetime import date, timedelta
from time import sleep
from pprint import pprint
import requests
import bs4
from bs4 import BeautifulSoup, ResultSet
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
        pprint(self.meeting_name)
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


class Topic:
    def __init__(self, topic_elm: bs4.element.Tag):
        self.title = self.__get_title(topic_elm)

    def __get_title(self, topic_elm):
        return topic_elm.text


class Speaker:
    def __init__(self, speaker_elm: bs4.element.Tag):
        self.name = self.__get_name(speaker_elm)
        self.attributes = self.__get_attributes(speaker_elm)

    def __get_name(self, speaker_elm):
        return re.sub("\(.+?\)", "", speaker_elm.text)

    def __get_attributes(self, speaker_elm):
        attributes_str = re.search(
            "(?<=\().+?(?=\))", speaker_elm.text).group()
        return attributes_str.split('・')


class MeetingDetails:
    def __init__(self, topics: list[Topic], speakers: list[Speaker]):
        self.topics = topics
        self.speakers = speakers


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
        pprint(self.speaker_time_list)

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
        return [topic_row.select_one(
            'td[width="595"]').text for topic_row in title_eliminated]

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
        topics_elm = self.topics_table.select('td[width="595"]')
        topics = [Topic(topic_elm) for topic_elm in topics_elm]
        speakers_elm = self.speakers_time_table_with_responder_ministers.select(
            'td[width="380"] a')
        speakers = [Speaker(speaker_elm) for speaker_elm in speakers_elm]
        return MeetingDetails(topics, speakers)


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
            "speakers": [{speaker.name: speaker.attributes} for speaker in self.meeting_details.speakers]
        }


class MeetingDownloader:
    def __init__(self, meeting_date):
        search_results_downloader = MeetingSearchDownloader(meeting_date)
        meeting_search_results = search_results_downloader.get_meeting_search_results()
        self.meetings = [MeetingInfo(meeting_summary, meeting_summary.get_meeting_details()).meeting_info_dict
                         for meeting_summary in meeting_search_results]


meeting_start_date = date(2022, 10, 13)
meetings = {}
for i in range(1):
    meeting_date = meeting_start_date + timedelta(days=i)
    meetings[meeting_date] = MeetingDownloader(meeting_date).meetings
    print(f"{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日の情報を取得中")
    sleep(1)

pprint(meetings)
