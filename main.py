from datetime import date
from shugiin_hatsugen import MeetingsDownloader as ShugiinMeetingsDownloader
from shugiin_hatsugen import DietMemberDownloader as ShugiinMemberDownloader
from sangiin_hatsugen import MeetingsDownloader as SangiinMeetingsDownloader
from sangiin_hatsugen import UpperHouseMembersDownloader as SangiinMemberDownloader
from giin_rippou import GiinRippouClient
from shuisho import ShugiinShuishoClient, SangiinShuishoClient
from excel_generator import ShugiinExcelGenerator, SangiinExcelGenerator

from config import\
    SHUGIIN_MEETING_CSV,\
    SHUGIIN_MEMBERS_CSV,\
    SHUGIIN_RIPPOU_CSV,\
    SHUGIIN_SHUISHO_CSV,\
    SHUGIIN_OUTPUT_FILE_NAME,\
    SANGIIN_MEETING_CSV,\
    SANGIIN_MEMBERS_CSV,\
    SANGIIN_RIPPOU_CSV,\
    SANGIIN_SHUISHO_CSV,\
    SANGIIN_OUTPUT_FILE_NAME,\
    DATE_START,\
    DATE_END

DOWNLOAD = True

DOWNLOAD_SHUGIIN_MEETING = False
DOWNLOAD_SHUGIIN_MEMBERS = False
DOWNLOAD_SHUGIIN_RIPPOU = False
DOWNLOAD_SHUGIIN_SHUISHO = False
DOWNLOAD_SANGIIN_MEETING = False
DOWNLOAD_SANGIIN_MEMBERS = False
DOWNLOAD_SANGIIN_RIPPOU = False
DOWNLOAD_SANGIIN_SHUISHO = True

# 衆議院
if (DOWNLOAD):
    ## 発言
    if (DOWNLOAD_SHUGIIN_MEETING):
        print('衆議院議員の発言を収集中...')
        shugiin_meetings_downloader = ShugiinMeetingsDownloader(DATE_START, DATE_END)
        shugiin_meetings_df = shugiin_meetings_downloader.meetings_df
        shugiin_meetings_df.to_csv(SHUGIIN_MEETING_CSV)
        print('完了')

    ## 議員
    if (DOWNLOAD_SHUGIIN_MEMBERS):
        print('衆議院議員の一覧を収集中...')
        shugiin_member_downloader = ShugiinMemberDownloader()
        shugiin_members_df = shugiin_member_downloader.diet_members_df
        shugiin_members_df.to_csv(SHUGIIN_MEMBERS_CSV)
        print('完了')

    # 議員立法
    if (DOWNLOAD_SHUGIIN_RIPPOU):
        print('衆議院議員の議員立法を収集中...')
        shugiin_rippou_client = GiinRippouClient(True)
        shugiin_rippou_df = shugiin_rippou_client.generate_page_df()
        shugiin_rippou_df.to_csv(SHUGIIN_RIPPOU_CSV)
        print('完了')

    # 主意書
    if (DOWNLOAD_SHUGIIN_SHUISHO):
        print('衆議院議員の主意書を収集中...')
        shugiin_shuisho_client = ShugiinShuishoClient()
        shugiin_shuisho_df = shugiin_shuisho_client.generate_questions_df()
        shugiin_shuisho_df.to_csv(SHUGIIN_SHUISHO_CSV)
        print('完了')

    # 参議院
    ## 発言
    if (DOWNLOAD_SANGIIN_MEETING):
        print('参議院議員の発言を収集中...')
        sangiin_meetings_downloader = SangiinMeetingsDownloader()
        sangiin_meetings_df = sangiin_meetings_downloader.meetings_df
        sangiin_meetings_df.to_csv(SANGIIN_MEETING_CSV)
        print('完了')

    ## 議員
    if (DOWNLOAD_SANGIIN_MEMBERS):
        print('参議院議員の一覧を収集中...')
        sangiin_member_downloader = SangiinMemberDownloader()
        sangiin_member_df = sangiin_member_downloader.upper_house_members_df
        sangiin_member_df.to_csv(SANGIIN_MEMBERS_CSV)
        print('完了')

    # 議員立法
    if (DOWNLOAD_SANGIIN_RIPPOU):
        print('参議院議員の議員立法を収集中...')
        sangiin_rippou_client = GiinRippouClient(False)
        sangiin_rippou_df = sangiin_rippou_client.generate_page_df()
        sangiin_rippou_df.to_csv(SANGIIN_RIPPOU_CSV)
        print('完了')

    # 主意書
    if (DOWNLOAD_SANGIIN_SHUISHO):
        print('参議院議員の主意書を収集中...')
        sangiin_shuisho_client = SangiinShuishoClient()
        sangiin_shuisho_df = sangiin_shuisho_client.generate_questions_df()
        sangiin_shuisho_df.to_csv(SANGIIN_SHUISHO_CSV)
        print('完了')

# 納品ファイル
print('衆議院の納品ファイルを生成中...')
shugiin_excel_generator = ShugiinExcelGenerator()
shugiin_excel_generator.generate(SHUGIIN_OUTPUT_FILE_NAME)
print('完了')

print('参議院の納品ファイルを生成中...')
sangiin_excel_generator = SangiinExcelGenerator()
sangiin_excel_generator.generate(SANGIIN_OUTPUT_FILE_NAME)
print('完了')