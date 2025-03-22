import requests
from datetime import datetime, timedelta
from environs import Env
from terminaltables import AsciiTable

HH_API_URL = "https://api.hh.ru/vacancies"
SJ_API_URL = "https://api.superjob.ru/2.0/vacancies/"
LANGUAGES = [
    "Python", "Java", "JavaScript", "C++", "C#",
    "Go", "Ruby", "PHP", "Shell", "Scala"
]
MOSCOW_AREA_ID = 1


def get_vacancies_hh(lang):
    total_vacancies = 0
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    salaries = []
    page = 0
    pages = 1

    while page < pages:
        params = {
            "text": f"программист {lang}",
            "area": MOSCOW_AREA_ID,
            "date_from": date_from,
            "per_page": 100,
            "page": page,
        }

        response = requests.get(HH_API_URL, params=params)
        response.raise_for_status()
        answer = response.json()
        vacancies = answer.get("items", [])
        pages = answer.get("pages", 1)
        total_vacancies = answer.get("found", 0)

        for vacancy in vacancies:
            salary = vacancy.get("salary")
            if not salary or salary.get("currency") != "RUR":
                continue

            predicted_salary = predict_salary(salary.get("from"),
                                              salary.get("to"))
            if predicted_salary:
                salaries.append(predicted_salary)

        page += 1

    return salaries, total_vacancies


def get_vacancies_sj(lang, api_key):
    total_vacancies = 0
    salaries = []
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

        response = requests.get(SJ_API_URL, headers=headers,
                                params=params)
        response.raise_for_status()
        answer = response.json()
        vacancies_sj = answer.get("objects", [])
        pages = answer.get("total", 1) // 100 + 1
        total_vacancies = answer.get("total", 0) or 0

        for vacancy in vacancies_sj:
            salary_from = vacancy.get("payment_from")
            salary_to = vacancy.get("payment_to")
            currency = vacancy.get("currency")

            if currency != "rub":
                continue

            predicted_salary = predict_salary(salary_from, salary_to)
            if predicted_salary:
                salaries.append(predicted_salary)

        page += 1

    return salaries, total_vacancies


def predict_salary(salary_from, salary_to):
    salary_increase_factor = 1.2
    salary_decrease_factor = 0.8
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * salary_increase_factor
    elif salary_to:
        return salary_to * salary_decrease_factor
    return


def get_average_salary(salaries):
    if not salaries:
        return None, 0

    average_salary = int(sum(salaries) / len(salaries))
    return average_salary


def collect_statistics_hh():
    hh_salary_stats = {}

    for lang in LANGUAGES:
        hh_salaries, vacancies_found = get_vacancies_hh(lang)
        avg_salary = get_average_salary(hh_salaries)
        vacancies_processed = len(hh_salaries)
        hh_salary_stats[lang] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": avg_salary
        }

    return hh_salary_stats


def collect_statistics_sj(api_key):
    sj_salary_stats = {}

    for lang in LANGUAGES:
        sj_salaries, vacancies_found = get_vacancies_sj(lang, api_key)
        avg_salary = get_average_salary(sj_salaries)
        vacancies_processed = len(sj_salaries)
        sj_salary_stats[lang] = {
            "vacancies_found": vacancies_found,
            "vacancies_processed": vacancies_processed,
            "average_salary": avg_salary
        }

    return sj_salary_stats


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
