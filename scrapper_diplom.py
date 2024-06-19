
import requests
import csv
from functools import lru_cache
import time
from tqdm import tqdm

def attempts(func):
    def wrapper(*args, **kwargs):
        res = None
        a = 0
        while res is None or a<5:
            a += 1
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if a < 5:
                    print('!!!SLEEP!!!')
                    time.sleep(5)
                else:
                    print(f'EXCEPTION: {e}')
                    return None

    return wrapper

# Функция для получения информации о нескольких пользователях
@attempts
def get_users_info(token, user_ids):
    url = 'https://api.vk.com/method/users.get'
    params = {
        'user_ids': ','.join(user_ids),
        'fields': 'bdate,education,followers_count,sex,city,country,home_town,contacts,site,status,occupation,activities,interests,music,movies,tv,books,games,about,quotes',
        'access_token': token,
        'v': '5.131'
    }
    response = requests.get(url, params=params).json()
    if 'error' in response:
        raise Exception(response['error'])
    return response['response'] if 'response' in response else None

# Функция для получения списка аудиозаписей пользователя
@attempts
def get_user_audio(token, user_id):
    url = 'https://api.vk.com/method/audio.get'
    params = {
        'owner_id': user_id,
        'access_token': token,
        'v': '5.131'
    }
    response = requests.get(url, params=params).json()
    if 'error' in response:
        raise Exception(response['error'])
    return response['response']['items'] if 'response' in response else None

# Функция для получения списка групп пользователя
@attempts
def get_user_groups(token, user_id):
    url = 'https://api.vk.com/method/groups.get'
    params = {
        'user_id': user_id,
        'extended': 1,
        'fields': 'description',
        'access_token': token,
        'v': '5.131'
    }
    response = requests.get(url, params=params).json()
    if 'error' in response:
        raise Exception(response['error'])
    return response['response']['items'] if 'response' in response else None


@lru_cache
@attempts
def get_posts(token, group_id, count=20):
    url = 'https://api.vk.com/method/wall.get'
    params = {
        'owner_id': -group_id,  # отрицательный ID для групп
        'count': count,
        'access_token': token,
        'v': '5.131'
    }
    response = requests.get(url, params=params).json()
    if 'error' in response:
        raise Exception(response['error'])
    items = []
    if 'response' in response:
        for item in response['response']['items']:
            items.append({
                'id': item['id'],
                'date': item['date'],
                'comments_count': item['comments']['count'],
                'likes_count': item['likes']['count'],
                'views_count': item['views']['count'],
                'text': item['text']
            })
    return items


@lru_cache
@attempts
def get_post_likes(token, group_id, post_id):
    url = 'https://api.vk.com/method/wall.getLikes'
    likes = []
    offset = 0
    while True:
        params = {
            'owner_id': -group_id,  # отрицательный ID для групп
            'post_id': post_id,
            'count': 1000,
            'offset': offset,
            'access_token': token,
            'v': '5.131'
        }
        response = requests.get(url, params=params).json()
        if 'error' in response:
            raise Exception(response['error'])
        users = response.get('response', {}).get('users')
        if not users:
            break
        
        likes += [user['uid'] for user in users]
    
        offset += 1000
    return likes


# Функция для получения комментариев пользователя в группе
@lru_cache
@attempts
def get_post_comments(token, group_id, post_id):
    url = 'https://api.vk.com/method/wall.getComments'
    comments = {}
    offset = 0
    while True:
        params = {
            'owner_id': -group_id,  # отрицательный ID для групп
            'post_id': post_id,
            'count': 100,
            'offset': offset,
            'access_token': token,
            'v': '5.131'
        }
        response = requests.get(url, params=params).json()
        if 'error' in response:
            raise Exception(response['error'])
        items = response.get('response', {}).get('items')
        if not items:
            break
        
        comments.update({item['from_id']: item['text'] for item in items})
    
        offset += 100
    return comments


def save_user(user_info, csv_writer):
    user_id = user_info['id']
    fio = f"{user_info.get('first_name')} {user_info.get('last_name')}"
    print(f"user_id={user_id} {fio}")
    is_closed = 'Закрытая' if user_info.get('is_closed') else 'Открытая'
    bdate = user_info.get('bdate', 'Не указана')
    sex = 'Мужской' if user_info.get('sex') == 2 else 'Женский' if user_info.get('sex') == 1 else 'Не указан'
    city = user_info.get('city', {}).get('title', 'Не указан')
    country = user_info.get('country', {}).get('title', 'Не указана')
    home_town = user_info.get('home_town', 'Не указан')
    contacts = f"{user_info.get('mobile_phone', 'Не указан')}, {user_info.get('home_phone', 'Не указан')}"
    site = user_info.get('site', 'Не указан')
    status = user_info.get('status', 'Не указан')
    occupation = user_info.get('occupation', {}).get('name', 'Не указан')
    activities = user_info.get('activities', 'Не указана')
    interests = user_info.get('interests', 'Не указаны')
    music = user_info.get('music', 'Не указана')
    movies = user_info.get('movies', 'Не указаны')
    tv = user_info.get('tv', 'Не указано')
    books = user_info.get('books', 'Не указаны')
    games = user_info.get('games', 'Не указаны')
    about = user_info.get('about', 'Не указано')
    quotes = user_info.get('quotes', 'Не указаны')

    csv_writer.writerow([
        user_id, fio, is_closed, bdate, sex, city, country, home_town, contacts, site, status, occupation,
        activities, interests, music, movies, tv, books, games, about, quotes
    ])

def proccess_user_activity(token, group_id, user_id, csv_writer):
    posts = get_posts(token, group_id)
    user_activity = []

    for post in tqdm(posts):
        is_like = bool(user_id in get_post_likes(token, group_id, post['id']))
        comment = get_post_comments(token, group_id, post['id']).get(user_id)
        if comment or is_like:
            user_activity.append({
                'user_id': user_id,
                'group_id': group_id,
                'post_id': post['id'],
                'date': post['date'],               
                'comment': comment,
                'like': is_like,
                'text': post['text'],
            })
            csv_writer.writerow([
                user_id, group_id, post['id'], post['date'], comment, is_like, post['text']
            ])
    
    return user_activity


# Основная логика
def main(token, user_ids):
    user_ids = [user_id.strip() for user_id in user_ids]

        
    # Открываем файл для записи информации о пользователях
    user_file = open('users_info.csv', 'w', newline='', encoding='utf-8')
    user_activity_file = open('user_activity.csv', 'w', newline='', encoding='utf-8')
    group_file = open('groups_info.csv', 'w', newline='', encoding='utf-8')
    
    # Заполнение header в файлах
    user_writer = csv.writer(user_file)
    user_writer.writerow([
        'ID', 'ФИО', 'Страница', 'Дата рождения', 'Пол', 'Город', 'Страна', 'Родной город', 'Контакты', 'Сайт',
        'Статус', 'Род занятий', 'Деятельность', 'Интересы', 'Музыка', 'Фильмы', 'ТВ', 'Книги', 'Игры', 'О себе', 'Цитаты'
    ])
    activity_writer = csv.writer(user_activity_file)
    activity_writer.writerow([
        'user_id', 'group_id', 'post_id', 'dt', 'comment', 'is_like', 'post_text',
    ])

    group_writer = csv.writer(group_file)
    group_writer.writerow(['ID пользователя', 'ID группы', 'Название группы', 'Тип', 'Описание',])

    # Начало сбора данных
    users_info = get_users_info(token, user_ids)
    if users_info:
        for user_info in users_info:
            user_id = user_info['id']
            save_user(user_info, user_writer)

            user_groups = get_user_groups(token, user_id)
            if user_groups:
                for i, group in enumerate(user_groups):
                    print(f"{i} group_id={group['id']} group_name={group['name']}")
                    group_writer.writerow([user_id, group['id'], group['name'], group.get('type'), group.get('description')])

                    if i < 10:
                        with open('groups_comment.csv', 'a', newline='', encoding='utf-8') as groups_comment_file:
                            proccess_user_activity(token, group['id'], user_id, activity_writer)

    user_file.close()
    user_activity_file.close()
    group_file.close()
    
if __name__ == "__main__":
    token = 'vk1.a.OBZFpPHE2V-dMXEW7V7TZ0aoS1T42tlE5EwKLpLzMVuX3xNZjxJchLXdTljD4ClfysvcCMp696zkmmIgPaHYNHB4IBEosEmL-sbT6pp4U7Lw658ywSP6oklKCOhZRwKyh2x3MxmNTRIs9GN4KH9BgvjnX8s3oGtX0_aLUHU2SummQZElQpDp_US_syDtD4aHyDcZnp7rnyylneSuhY9kRg'  # Вставьте ваш токен доступа
    user_ids = ['l_e_i_k_a', 'a_vinnikov']
    main(token, user_ids)
