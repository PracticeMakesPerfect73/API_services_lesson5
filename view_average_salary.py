import requests
from datetime import datetime, timedelta
from environs import Env
from terminaltables import AsciiTable

API_URL_HH = "https://api.hh.ru/vacancies"
API_URL_SJ = "https://api.superjob.ru/2.0/vacancies/"
LANGUAGES = [
    "Python", "Java", "JavaScript", "C++", "C#",
    "Go", "Ruby", "PHP", "Shell", "Scala"
]
MOSCOW_AREA_ID = 1


def get_vacancies_count_hh():
    vacancies_count = {}

    for lang in LANGUAGES:
        params = {
            "text": f"программист {lang}",
            "area": MOSCOW_AREA_ID,
        }
        response = requests.get(API_URL_HH, params=params)
        response.raise_for_status()
        answer = response.json()
        vacancies_count[lang] = answer.get("found", 0)

    return vacancies_count


def get_vacancies_count_sj(api_key):
    vacancies_count = {}
    headers = {"X-Api-App-Id": api_key}

    for lang in LANGUAGES:
        params = {
            "keywords": lang,
            "town": "Москва",
            "count": 1
        }
        response = requests.get(API_URL_SJ, headers=headers, params=params)
        response.raise_for_status()
        total_found = response.json().get("total", 0) or 0
        vacancies_count[lang] = total_found

    return vacancies_count


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    return None


def predict_rub_salary_hh(lang):
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    salaries_hh = []
    page = 0
    pages = 1

    while page < pages:
        params = {
            "text": f"программист {lang}",
            "area": MOSCOW_AREA_ID,
            "date_from": date_from,
            "per_page": 100,
            "page": page,
            "only_with_salary": True
        }

        response = requests.get(API_URL_HH, params=params)
        response.raise_for_status()
        answer = response.json()
        vacancies_hh = answer.get("items", [])
        pages = answer.get("pages", 1)

        for vacancy in vacancies_hh:
            salary = vacancy.get("salary")
            if not salary or salary.get("currency") != "RUR":
                continue

            predicted_salary = predict_salary(salary.get("from"),
                                              salary.get("to"))
            if predicted_salary:
                salaries_hh.append(predicted_salary)

        page += 1

    return salaries_hh


def predict_rub_salary_sj(lang, api_key):
    salaries_sj = []
    page = 0
    pages = 1
    headers = {"X-Api-App-Id": api_key}

    while page < pages:
        params = {
            "keywords": lang,
            "town": "Москва",
            "count": 100,
            "page": page
        }

        response = requests.get(API_URL_SJ, headers=headers,
                                params=params)
        response.raise_for_status()
        answer = response.json()
        vacancies_sj = answer.get("objects", [])
        pages = answer.get("total", 1) // 100 + 1

        for vacancy in vacancies_sj:
            salary_from = vacancy.get("payment_from")
            salary_to = vacancy.get("payment_to")
            currency = vacancy.get("currency")

            if currency != "rub":
                continue

            predicted_salary = predict_salary(salary_from, salary_to)
            if predicted_salary:
                salaries_sj.append(predicted_salary)

        page += 1

    return salaries_sj


def get_average_salary(salaries):
    if not salaries:
        return None, 0

    average_salary = int(sum(salaries) / len(salaries))
    return average_salary, len(salaries)


def collect_statistics_hh():
    vacancies_count = get_vacancies_count_hh()
    salary_stats_hh = {}

    for lang in LANGUAGES:
        salaries_hh = predict_rub_salary_hh(lang)
        avg_salary, processed = get_average_salary(salaries_hh)
        salary_stats_hh[lang] = {
            "vacancies_found": vacancies_count[lang],
            "vacancies_processed": processed,
            "average_salary": avg_salary
        }

    return salary_stats_hh


def collect_statistics_sj(api_key):
    vacancies_count = get_vacancies_count_sj(api_key)
    salary_stats_sj = {}

    for lang in LANGUAGES:
        salaries_sj = predict_rub_salary_sj(lang, api_key)
        avg_salary, processed = get_average_salary(salaries_sj)
        salary_stats_sj[lang] = {
            "vacancies_found": vacancies_count[lang],
            "vacancies_processed": processed,
            "average_salary": avg_salary
        }

    return salary_stats_sj


def print_table(statistics, source_name):
    table_data = [
        [
            "Язык программирования", "Вакансий найдено",
            "Вакансий обработано", "Средняя зарплата"
        ]
    ]

    for lang, vacancy_stats in statistics.items():
        table_data.append([
            lang, vacancy_stats["vacancies_found"],
            vacancy_stats["vacancies_processed"],
            vacancy_stats["average_salary"]
        ])

    table_instance = AsciiTable(table_data, source_name)
    table_instance.justify_columns[2] = "right"
    print(table_instance.table)
    print()


def main():
    env = Env()
    env.read_env()
    api_key = env.str("SJ_API_KEY")
    statistics_hh = collect_statistics_hh()
    print_table(statistics_hh, source_name='HeadHunter Moscow')

    statistics_sj = collect_statistics_sj(api_key)
    print_table(statistics_sj, source_name='SuperJob Moscow')


if __name__ == "__main__":
    main()
