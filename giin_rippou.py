import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from selenium.webdriver import Chrome
from time import sleep
from selenium.webdriver.chrome.options import Options

from config import MEETING_TERM

URL_BASE = 'https://hourei.ndl.go.jp/law/api/v1/search/detail?'
PER_PAGE = 100
SHUGIIN_PARAM = f'fw=&fwc=and&bill.t1=false&bill.t2=true&bill.t3=false&bill.t4=false&bill.t11=false&bill.t12=false&bill.t13=false&bill.t14=false&bill.t1516=false&bill.tef=5&bill.tper=range&bill.tet=5&bill.tdcf=1&bill.tsf={MEETING_TERM}&bill.tsp=range&bill.tdct=1&bill.epef=5&bill.epp=range&bill.epet=5&bill.ptp=false&bill.discussList[0].sd=1&bill.discussList[0].ode=5&bill.bdin=false&bill.bdr=false&bill.bda=false&bill.bde=false&bill.adef=5&bill.adp=range&bill.adet=5&bill.adf=1&bill.asp=range&bill.adt=1&bill.epe=5&type=&div=&order=1&perpage={PER_PAGE}'
SANGIIN_PARAM = f'fw=&fwc=and&bill.t1=false&bill.t2=false&bill.t3=true&bill.t4=false&bill.t11=false&bill.t12=false&bill.t13=false&bill.t14=false&bill.t1516=false&bill.tef=5&bill.tper=range&bill.tet=5&bill.tdcf=1&bill.tsf={MEETING_TERM}&bill.tsp=range&bill.tdct=1&bill.epef=5&bill.epp=range&bill.epet=5&bill.ptp=false&bill.discussList%5B0%5D.sd=1&bill.discussList%5B0%5D.ode=5&bill.bdin=false&bill.bdr=false&bill.bda=false&bill.bde=false&bill.adef=5&bill.adp=range&bill.adet=5&bill.adf=1&bill.asp=range&bill.adt=1&bill.epe=5&type=&div=&order=1&perpage={PER_PAGE}'

class GiinRippouClient:
    def __init__(self, is_shugiin):
        if (is_shugiin):
            self.url_base = URL_BASE + SHUGIIN_PARAM
        else:
            self.url_base = URL_BASE + SANGIIN_PARAM

        self.options = Options()
        self.options.add_argument('--headless')

    def generate_page_df(self):
        search_page_data_list = self.download_search_pages()
        bill_ids = self.get_bill_ids(search_page_data_list)
        submitters_info_list = self.download_submitters_info(bill_ids)
        return pd.DataFrame(submitters_info_list)

    def download_submitters_info(self, bill_ids):
        submitters_info_list = []
        driver = Chrome(options=self.options)
        for bill_id in bill_ids:
            print(f'https://hourei.ndl.go.jp/#/detail?billId={bill_id} の情報を取得中')
            driver.get(f'https://hourei.ndl.go.jp/#/detail?billId={bill_id}')
            sleep(2)
            bill_page_response = driver.page_source.encode('utf-8')
            bill_page_bs4 = BeautifulSoup(bill_page_response, 'html.parser')
            submitters_info_by_law_list = self.parse_bill_page(bill_id, bill_page_bs4)
            if submitters_info_by_law_list:
                submitters_info_list.extend(submitters_info_by_law_list)
        driver.quit()
        return submitters_info_list

    def parse_bill_page(self, bill_id, bill_page_bs4):
        li_list = bill_page_bs4.find_all('li')
        #checker =[f'{i} : {content}' for (i, content) in enumerate(li_list)]
        #pprint(checker)
        
        if (not self.is_submitted_by_member(li_list)):
            law_submitter_row_elm = li_list[14]
            law_submitter_elm = law_submitter_row_elm.find_all('div')[-1]
            law_submitter = law_submitter_elm.text.strip()
            print(f'{law_submitter}から提出されたものであるためスキップしました。')
            return
        else:
            law_title_row_elm = li_list[8]
            law_title_elm = law_title_row_elm.find_all('div')[-1]
            law_title = law_title_elm.text
            #print(law_title)

            law_number_row_elm = li_list[11]
            law_number_elm = law_number_row_elm.find_all('div')[-1]
            law_number = law_number_elm.text
            #print(law_number)

            law_represent_submitter_row_elm = li_list[12]
            law_represent_submitter_elm = law_represent_submitter_row_elm.find_all('div')[-1]
            law_represent_submitter = law_represent_submitter_elm.text.strip().split('、')[0]
            #print(law_represent_submitter)

            law_other_submitters_row_elm = li_list[13]
            law_other_submitters_elm = law_other_submitters_row_elm.find_all('div')[-1]
            law_other_submitters = law_other_submitters_elm.text.split(',')
            #print(law_other_submitters)

            law_submitters = []
            law_submitters.append(law_represent_submitter)
            law_submitters.extend(law_other_submitters)
            #print(law_submitters)

            if (self.is_submitted_by_leader(law_represent_submitter)):
                print(f'{law_represent_submitter}から提出されたものであるためスキップしました。')
                return

            law_info_list = []
            for law_submitter in law_submitters:
                law_dict = {
                    'bill_id': bill_id,
                    '提出番号': law_number,
                    '法律案名': law_title,
                    '提出者': law_submitter
                }
                law_info_list.append(law_dict)
            return law_info_list

    def is_submitted_by_member(self, li_list):
        law_number_row_elm = li_list[11]
        law_number_elm = law_number_row_elm.find_all('div')[-1]
        law_number = law_number_elm.text
        return law_number != f'第{MEETING_TERM}回国会'

    def is_submitted_by_leader(self, law_represent_submitter):
        return '委員長' in law_represent_submitter

    def get_bill_ids(self, page_data_list):
        return [page_data['bill_id'] for page_data in page_data_list]

    def get_total_search_pages(self) -> int:
        page_info_json_str = requests.get(self.url_base)
        page_info_json = json.loads(page_info_json_str.content)
        total_pages = page_info_json['total_pages']
        return total_pages

    def __get_page_param(self, page_num: int) -> str:
        return f'&page={page_num}'

    def download_search_page(self, page_num: int) -> dict:
        page_info_json_str = requests.get(self.url_base + self.__get_page_param(page_num))
        return json.loads(page_info_json_str.content)

    def download_search_pages(self) -> list:
        total_pages = self.get_total_search_pages()
        page_data_list = []
        for i in range(0, total_pages):
            page_info_json = self.download_search_page(i)
            current_page_data = page_info_json['data']
            page_data_list.extend(current_page_data)
        return page_data_list