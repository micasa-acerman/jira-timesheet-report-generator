from jira import JIRA
import csv
from dateutil import parser
import pytz


BLOCK = 10
jira_options = {'server': '',
                'login': '',  # Почта указанная в профиле
                'api_key': '',  # Ключ для аунтификации
                'project_key': '',
                'start_at': '2021-07-01'}  # Используется для фильтрации зарегистрированного времени(в отчет попадут задачи с зарегистрированным временем не раньше заданного)
utc = pytz.UTC
start_date = utc.localize(parser.parse(jira_options['start_at']))

jira = JIRA(options=jira_options, basic_auth=(
    jira_options['login'], jira_options['api_key']))
accountId = jira.current_user(field="accountId")


def flatten(list_of_lists):
    return [val for sublist in list_of_lists for val in sublist]


def seconds_to_human_format(seconds):
    d = int(seconds / 28800)
    h = int((seconds - (d * 28800)) / 3600)
    m = int((seconds - (d * 28800 + h * 3600)) / 60)
    s = int((seconds - (d * 28800 + h * 3600 + m * 60)))

    result = ''
    if d > 0:
        result += f'{d}d '
    if h > 0:
        result += f'{h}h '
    if m > 0:
        result += f'{m}m '
    if s > 0:
        result += f'{s}s'
    return result


def get_data(jql):
    result = []
    offset = 0
    while(True):
        issues = jira.search_issues(jql, maxResults=BLOCK, startAt=offset)
        data = flatten([get_elapsed_time(issue.key) for issue in issues])
        filtered_data = [item for item in data if item['spent_time'] > 0]
        result += filtered_data
        if (issues.total-offset-BLOCK) / BLOCK > 0:
            offset += BLOCK
        else:
            return [dict(t) for t in {tuple(d.items()) for d in result}]
        print(f'Прогресс {round(offset*100.0/issues.total)}%')


def get_elapsed_time(issue_key):
    issue = jira.issue(issue_key)
    summary_spent_time = sum([log.timeSpentSeconds for log in issue.fields.worklog.worklogs
                              if accountId == log.author.accountId and utc.localize(parser.parse(log.updated.split('.')[0])) >= start_date])
    formated_date = seconds_to_human_format(summary_spent_time)
    result = []
    if(True):
        result.append({'key': issue_key,
                       'href': jira_options['server']+'/browse/'+issue_key,
                       'title': issue.fields.summary,
                       'status': issue.fields.status.name,
                       'spent_time': summary_spent_time,
                       'formatted_spent_time': formated_date})
    if(len(issue.fields.subtasks) > 0):
        subtasks = flatten([get_elapsed_time(task.key)
                           for task in issue.fields.subtasks])
        result = result + subtasks
    return result


jql = f'project="{jira_options["project_key"]}" and worklogDate>="{jira_options["start_at"]}" ORDER BY updated DESC'
data = get_data(jql)
total_amount = seconds_to_human_format(
    sum([item['spent_time'] for item in data]))

with open(f'report_{jira_options["start_at"]}.csv', 'w', newline='') as csvfile:
    csv_writter = csv.DictWriter(csvfile, delimiter=',',
                                 quotechar='"', quoting=csv.QUOTE_ALL, fieldnames=['key', 'href', 'title', 'status', 'priority', 'formatted_spent_time', 'spent_time'])

    csv_writter.writer.writerow(['Идентификатор', 'Ссылка', 'Задача', 'Статус',
                                'Приоритет', 'Затраченное время', 'Затраченное время (в секундах)'])
    csv_writter.writerows(data)
    csv_writter.writer.writerow([f'Итого: {total_amount}'])
