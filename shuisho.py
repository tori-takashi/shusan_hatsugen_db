import requests
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint

from config import MEETING_TERM

SHUGIIN_SHUISHO_URL_BASE = "https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon/"
SANGIIN_SHUISHO_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/syuisyo/"+str(MEETING_TERM)+"/syuisyo.htm"

class PageNotFoundError(Exception):
    pass

class ShugiinShuishoClient:
    def __init__(self):
        pass

    def generate_questions_df(self):
        questions = self.download_questions()
        return pd.DataFrame(questions)

    def download_questions(self):
        question_index = 1
        questions = []
        while(True):
            try:
                question_bs4 = self.download_question_page(question_index)
            except:
                break
            question_dict = self.parse_question_page(question_bs4)
            questions.append(question_dict)
            question_index += 1
        return questions

    def download_question_page(self, question_index: int):
        shugiin_questions_response = requests.get(SHUGIIN_SHUISHO_URL_BASE+ str(MEETING_TERM)+ "{:03}.htm".format(question_index))
        if (shugiin_questions_response.status_code == 404):
            raise PageNotFoundError
        return BeautifulSoup(shugiin_questions_response.content, 'html.parser')

    def parse_question_page(self, question_bs4):
        question_content_rows = question_bs4.find_all('tr')

        question_number_content_row = question_content_rows[3]
        question_number = int(question_number_content_row.find_all('td')[1].text)

        question_title_content_row = question_content_rows[4]
        question_title = question_title_content_row.find_all('td')[1].text

        question_person_content_row = question_content_rows[5]
        question_person = question_person_content_row.find_all('td')[1].text.replace('\u3000', '')[:-1]

        question_dict = {
            '質問番号': question_number,
            '質問件名': question_title,
            '提出者名': question_person
        }

        print(question_dict['質問番号'], ':', question_dict['提出者名'], ':', question_dict['質問件名'])

        return question_dict


class SangiinShuishoClient:
    def __init__(self):
        pass

    def generate_questions_df(self):
        questions_bs4 = self.download_questions_page()
        questions = self.parse_questions_page(questions_bs4)
        return pd.DataFrame(questions)

    def download_questions_page(self):
        questions_response = requests.get(SANGIIN_SHUISHO_URL)
        return BeautifulSoup(questions_response.content, 'html.parser')

    def parse_questions_page(self, questions_bs4):
        question_list = []
        questions_table = questions_bs4.find_all('table')[1]
        question_rows = questions_table.find_all('tr')
        questions = [question_rows[i-3:i] for i in range(1, len(question_rows) + 1) if i % 3 == 0]
        for question in questions:
            question_number = int(question[1].find_all('td')[0].text.strip())
            question_title = question[0].find('td').text.strip()
            question_persion = question[1].find_all('td')[1].text.replace('\u3000', '')[:-1]
            question_dict = {
                '質問番号': question_number,
                '件名': question_title,
                '提出者': question_persion
            }
            print(question_dict['質問番号'], ':', question_dict['件名'], ':', question_dict['提出者'])
            question_list.append(question_dict)
        return question_list

