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

MEETINGS_URL_BASE = "https://www.shugiintv.go.jp/jp/"
MEETINGS_PARAM_BASE = "ex=VL"

MEETINGS_CSV_FILE_NAME = "shugiin_meetings.csv"
SHUGIIN_DIET_MEMBERS_CSV_FILE_NAME = "shugiin_diet_members.csv"

OUTPUT_FILE_NAME = "shugiin.xlsx"

# 会議


class MeetingSearchResult:
    def __init__(self, result_elm: bs4.element.Tag):
        self.meeting_name = self.__get_meeting_name(result_elm)
        self.meeting_detail_url = self.__get_meeting_detail_url(result_elm)

    def __get_meeting_name(self, result_elm) -> str:
        return result_elm.text

    def __get_meeting_detail_url(self, result_elm) -> str:
        url_filter = "\'.*?\'"
        href = result_elm.get('href')
        return MEETINGS_URL_BASE + re.sub("'", "", re.search(url_filter, href).group())

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
            MEETINGS_URL_BASE + "index.php?" + MEETINGS_PARAM_BASE + "&u_day=" + year_str + month_str + day_str)
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


class MeetingsDownloader:
    def __init__(self, meeting_start_date, meeting_end_date):
        self.meeting_start_date = meeting_start_date
        self.meeting_end_date = meeting_end_date
        self.meetings = {}
        self.meetings_row_dict_list = []
        self.download()
        self.meetings_df = pd.DataFrame(self.meetings_row_dict_list)

    def download(self):
        for i in range((self.meeting_end_date - self.meeting_start_date).days+1):
            meeting_date = self.meeting_start_date + timedelta(days=i)
            print(
                f"{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日の情報を取得中")
            meeting_info = MeetingDownloader(meeting_date).meetings

            self.__set_meetings_info(meeting_date, meeting_info)
            self.__set_meetings_row_dict_list(meeting_info)

            sleep(0.1)

    def __set_meetings_info(self, meeting_date: date, meeting_info: list[MeetingInfo]):
        self.meetings_row_dicts = [meeting.to_row_dict()
                                   for meeting in meeting_info]
        self.meetings[meeting_date] = meeting_info

    def __set_meetings_row_dict_list(self, meeting_info: list[MeetingInfo]):
        for meeting in meeting_info:
            for row_dict in meeting.to_row_dict():
                self.meetings_row_dict_list.append(row_dict)


# 衆議院議員

class DietMember:
    def __init__(self, name_kanji, name_kana, party):
        self.name_kanji = name_kanji
        self.name_kana = name_kana
        self.party = party

    def to_dict(self) -> dict:
        return {
            "name_kanji": self.name_kanji,
            "name_kana": self.name_kana,
            "party": self.party
        }


class DietMembersPage:
    def __init__(self, diet_members_bs4: BeautifulSoup):
        self.diet_members_bs4 = diet_members_bs4
        self.__diet_member_table = self.__get_diet_members_table()
        self.__diet_member_rows = self.__get_diet_member_rows()
        self.diet_members = self.__get_diet_members()

    def __get_diet_members_table(self) -> BeautifulSoup:
        diet_members_tables = self.diet_members_bs4.find(
            name="div", id='sh1body')
        return diet_members_tables.find_all(name="table")[1]

    def __get_diet_member_rows(self) -> BeautifulSoup:
        return self.__diet_member_table.find_all(name="tr")[2:]

    def __get_diet_members(self) -> list[DietMember]:
        diet_member_list = []
        for diet_member_row in self.__diet_member_rows:
            row_elm = diet_member_row.find_all(name="td")

            name_kanji_raw = row_elm[0]
            name_kanji = "".join(
                name_kanji_raw.text.split())[:-1]
            name_kana_raw = row_elm[1]
            name_kana = " ".join(
                name_kana_raw.text.split())
            party_raw = row_elm[2]
            party = party_raw.text.strip()
            diet_member_list.append(DietMember(name_kanji, name_kana, party))
        return diet_member_list


class DietMemberDownloader:
    def __init__(self):
        self.URL_BASE = "https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/"
        self.PAGE_NAME = "giin.htm"
        self.__diet_members_page_list = self.download_page()
        self.diet_members = self.get_diet_members()
        self.add_resigned_diet_members()
        self.diet_members_df = self.get_diet_members_df()

    def download_page(self) -> list[DietMembersPage]:
        diet_members_page_list = []
        for i in range(1, 11):
            url = self.URL_BASE + str(i) + self.PAGE_NAME
            print(url, "の情報を取得中")
            diet_members_response = requests.get(url)
            diet_members_bs4 = BeautifulSoup(
                diet_members_response.content, "html.parser")
            diet_members_page_list.append(DietMembersPage(diet_members_bs4))
            sleep(0.1)
        return diet_members_page_list

    def get_diet_members(self) -> list[DietMember]:
        diet_members_list = []
        for diet_members_page in self.__diet_members_page_list:
            diet_members_list.extend(diet_members_page.diet_members)
        return diet_members_list

    def add_resigned_diet_members(self):
        self.diet_members.append(DietMember(name_kanji="山田修路", name_kana="やまだ しゅうじ", party="自由民主党"))
        self.diet_members.append(DietMember(name_kanji="山本太郎", name_kana="やまもと たろう", party="れいわ新選組"))
        self.diet_members.append(DietMember(name_kanji="吉川赳", name_kana="よしかわ たける", party="自由民主党"))
        self.diet_members.append(DietMember(name_kanji="藤末健三", name_kana="ふじすえ けんぞう", party="自由民主党"))
        self.diet_members.append(DietMember(name_kanji="岸本周平", name_kana="きしもと しゅうへい", party="無所属"))


    def get_diet_members_df(self) -> pd.DataFrame:
        diet_members_dict_list = [diet_member.to_dict()
                                  for diet_member in self.diet_members]
        return pd.DataFrame(diet_members_dict_list)

# エクセルファイル生成


class GenerateExcel:
    def __init__(self, read_from_files, meetings_df=None, diet_members_df=None):
        self.read_from_files = read_from_files
        if (self.read_from_files):
            self.meetings_df = pd.read_csv(MEETINGS_CSV_FILE_NAME)
            self.diet_members_df = pd.read_csv(
                SHUGIIN_DIET_MEMBERS_CSV_FILE_NAME)
        else:
            self.meetings_df = meetings_df
            self.diet_members_df = diet_members_df

    def merge_df(self):
        return pd.merge(self.meetings_df, self.diet_members_df,
                        left_on="name", right_on="name_kanji", how='left').drop(columns=["name_kanji", "Unnamed: 0_x", "Unnamed: 0_y"])

    def get_blacklist_str(self):
        return "|".join(self.blacklist)

    def generate(self):
        self.blacklist = [
            "委員長",
            "大臣",
            "議長",
            "委員長",
            "会長",
            "主査",
            "長官",
            "担当",
            "参考人",
            "公述人",
            "局長",
            "採決",
            "総裁",
            "ウクライナ大統領",
            "日本弁護士連合会",
            "参議院"]

        self.merged_master = self.merge_df()
        self.merged_master = self.merged_master.reindex(
            columns=['date', 'meeting_name', 'name', 'name_kana', 'party', 'time_min', 'topics', 'attributes'])
        self.merged_master.rename(columns={
            "date": "日にち",
            "meeting_name": "委員会",
            "name": "議員名",
            "name_kana": "ふりがな",
            "party": "政党",
            "time_min": "時間",
            "topics": "案件",
            "attributes": "属性"
        }, inplace=True)
        self.merged_master.sort_values(
            ['議員名', '日にち'], inplace=True)
        self.merged_master.reset_index(inplace=True, drop=True)

        self.purified_by_blacklist = self.merged_master[~self.merged_master["属性"].str.contains(
            self.get_blacklist_str())]
        self.filtered_by_blacklist = self.merged_master[self.merged_master["属性"].str.contains(
            self.get_blacklist_str())]

        self.purified_by_time = self.purified_by_blacklist[self.purified_by_blacklist["時間"] > 3]
        self.filtered_by_time = self.purified_by_blacklist[~self.purified_by_blacklist["時間"] > 3]

        with pd.ExcelWriter(OUTPUT_FILE_NAME) as writer:
            self.purified_by_time.to_excel(writer, sheet_name="最終データ")
            self.filtered_by_time.to_excel(
                writer, sheet_name="抽出・ブラックリスト除去済み・1~3分")
            self.filtered_by_blacklist.to_excel(
                writer, sheet_name="抽出・ブラックリスト")
            self.merged_master.to_excel(writer, sheet_name="結合全データ")
            self.meetings_df.to_excel(writer, sheet_name="元データ・会議")
            self.diet_members_df.to_excel(writer, sheet_name="元データ・衆議院議員")


#meeting_start_date = date(2022, 1, 1)
#meeting_end_date = date(2022, 6, 30)
#meetings_downloader = MeetingsDownloader(meeting_start_date, meeting_end_date)
#meetings_df = meetings_downloader.meetings_df
#meetings_df.to_csv(MEETINGS_CSV_FILE_NAME)

#diet_member_downloader = DietMemberDownloader()
#diet_members_df = diet_member_downloader.diet_members_df
#diet_members_df.to_csv(SHUGIIN_DIET_MEMBERS_CSV_FILE_NAME)

#excel_generator = GenerateExcel(
    #read_from_files=False, meetings_df=meetings_df, diet_members_df=diet_members_df)

excel_generator = GenerateExcel(read_from_files=True)
excel_generator.generate()
