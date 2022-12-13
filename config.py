from datetime import date

# 共通設定
MEETING_TERM = 210

# 衆議院設定
DATE_START = date(2022, 8, 19)
DATE_END = date(2022, 12, 10)

# 参議院設定
SID_BEGIN = 7034
SID_END = 7199

# 衆議院ファイル
SHUGIIN_MEMBERS_CSV = '議員(衆議院).csv'
SHUGIIN_MEETING_CSV = '発言一覧(衆議院).csv'
SHUGIIN_SHUISHO_CSV = '主意書(衆議院).csv'
SHUGIIN_RIPPOU_CSV = '議員立法(衆議院).csv'
SHUGIIN_OUTPUT_FILE_NAME = '衆議院.xlsx'

# 参議院ファイル
SANGIIN_MEMBERS_CSV = '議員(参議院).csv'
SANGIIN_MEETING_CSV = '発言一覧(参議院).csv'
SANGIIN_SHUISHO_CSV = '主意書(参議院).csv'
SANGIIN_RIPPOU_CSV = '議員立法(参議院).csv'
SANGIIN_OUTPUT_FILE_NAME = '参議院.xlsx'
