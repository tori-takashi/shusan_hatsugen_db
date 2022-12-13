import pandas as pd
from config import\
    SHUGIIN_MEETING_CSV,\
    SHUGIIN_RIPPOU_CSV,\
    SHUGIIN_SHUISHO_CSV,\
    SHUGIIN_MEMBERS_CSV,\
    SANGIIN_MEETING_CSV,\
    SANGIIN_RIPPOU_CSV,\
    SANGIIN_SHUISHO_CSV,\
    SANGIIN_MEMBERS_CSV

class ShugiinExcelGenerator:
    def __init__(self):
        self.shugiin_meeting_df = pd.read_csv(SHUGIIN_MEETING_CSV)
        self.shugiin_members_df = pd.read_csv(SHUGIIN_MEMBERS_CSV)
        self.shugiin_shuisho_df = self.drop_unnamed(pd.read_csv(SHUGIIN_SHUISHO_CSV))
        self.shugiin_rippou_df = self.drop_unnamed(pd.read_csv(SHUGIIN_RIPPOU_CSV))

    def generate(self, filename):
        meetings_with_members_df = self.merge_meeting_members_df(
            self.shugiin_meeting_df, self.shugiin_members_df)
        passed_meetings_df, filtered_meetings_df = self.filter_blacklist(meetings_with_members_df)

        with pd.ExcelWriter(filename) as writer:
            self.shugiin_shuisho_df.to_excel(writer, sheet_name="⑦主意書")
            self.shugiin_rippou_df.to_excel(writer, sheet_name="⑥議員立法")
            passed_meetings_df.to_excel(writer, sheet_name="⑤③からブラックリストを弾いた最終データ")
            filtered_meetings_df.to_excel(writer, sheet_name="④③のうちブラックリストから抽出された発言")
            meetings_with_members_df.to_excel(writer, sheet_name="③会議発言①と衆議院議員②を結合")
            self.shugiin_members_df.to_excel(writer, sheet_name="②元データ・衆議院議員")
            self.shugiin_meeting_df.to_excel(writer, sheet_name="①元データ・会議発言")

    def drop_unnamed(self, df):
        return df.drop(
            columns=["Unnamed: 0"])

    def filter_blacklist(self, meetings_with_members_df):
        passed = meetings_with_members_df[
            ~meetings_with_members_df["属性"].str.contains(self.__get_blacklist_str())]
        filtered = meetings_with_members_df[
            meetings_with_members_df["属性"].str.contains(self.__get_blacklist_str())]
        return (passed, filtered)

    def __get_blacklist_str(self):
        blacklist = [
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
        return "|".join(blacklist)

    def merge_meeting_members_df(self, shugiin_meeting_df, shugiin_members_df):
        return pd.merge(
            shugiin_meeting_df,
            shugiin_members_df,
            left_on="name",
            right_on="name_kanji",
            how='left'
            ).drop(
            columns=["name_kanji", "Unnamed: 0_x", "Unnamed: 0_y"]
            ).reindex(
            columns=['date', 'meeting_name', 'name', 'name_kana', 'party', 'time_min', 'topics', 'attributes']
            ).rename(
            columns={
                "date": "日にち",
                "meeting_name": "委員会",
                "name": "議員名",
                "name_kana": "ふりがな",
                "party": "政党",
                "time_min": "時間",
                "topics": "案件",
                "attributes": "属性"},
            ).reset_index(
            drop=True)

class SangiinExcelGenerator:
    def __init__(self):
        self.sangiin_meeting_df = pd.read_csv(SANGIIN_MEETING_CSV)
        self.sangiin_members_df = pd.read_csv(SANGIIN_MEMBERS_CSV)
        self.sangiin_shuisho_df = self.drop_unnamed(pd.read_csv(SANGIIN_SHUISHO_CSV))
        self.sangiin_rippou_df = self.drop_unnamed(pd.read_csv(SANGIIN_RIPPOU_CSV))

    def generate(self, filename):
        meetings_with_members_df = self.merge_meeting_members_df(
            self.sangiin_meeting_df, self.sangiin_members_df)
        passed_meetings_df, filtered_meetings_df = self.filter_blacklist(meetings_with_members_df)

        with pd.ExcelWriter(filename) as writer:
            self.sangiin_shuisho_df.to_excel(writer, sheet_name="⑦主意書")
            self.sangiin_rippou_df.to_excel(writer, sheet_name="⑥議員立法")
            passed_meetings_df.to_excel(writer, sheet_name="⑤③からブラックリストを弾いた最終データ")
            filtered_meetings_df.to_excel(writer, sheet_name="④③のうちブラックリストから抽出された発言")
            meetings_with_members_df.to_excel(writer, sheet_name="③会議発言①と衆議院議員②を結合")
            self.sangiin_members_df.to_excel(writer, sheet_name="②元データ・衆議院議員")
            self.sangiin_meeting_df.to_excel(writer, sheet_name="①元データ・会議発言")

    def drop_unnamed(self, df):
        return df.drop(
            columns=["Unnamed: 0"])

    def filter_blacklist(self, meetings_with_members_df):
        passed = meetings_with_members_df[
            ~meetings_with_members_df["属性"].str.contains(self.__get_blacklist_str())]
        filtered = meetings_with_members_df[
            meetings_with_members_df["属性"].str.contains(self.__get_blacklist_str())]
        return (passed, filtered)

    def __get_blacklist_str(self):
        blacklist = [
            "委員長",
            "大臣",
            "議長",
            "委員長",
            "参考人",
            "総裁",
            "公述人",
            "長官",
            "総長",
            "局長",
            "院長",
            "会長",
            "衆議院議員"]
        return "|".join(blacklist)

    def merge_meeting_members_df(self, sangiin_meeting_df, sangiin_members_df):
        return pd.merge(
            sangiin_meeting_df,
            sangiin_members_df,
            left_on="name",
            right_on="name",
            how='left'
            ).drop(
            columns=["Unnamed: 0_x", "Unnamed: 0_y"]
            ).reindex(
            columns=['meeting_date', 'meeting_name', 'name', 'name_kana', 'time_min', 'meeting_content', 'attributes']
            ).rename(columns={
                "meeting_date": "日にち",
                "meeting_name": "委員会",
                "meeting_content": "案件",
                "name": "議員名",
                "name_kana": "ふりがな",
                "attributes": "属性",
                "time_min": "時間"}
            ).reset_index(
            drop=True)