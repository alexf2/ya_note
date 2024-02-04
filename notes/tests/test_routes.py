from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notes.models import Note
# from notes.models import Note
from notes.urls import app_name as notes

User = get_user_model()


class RoutesAnonimousTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='Автор 1')
        cls.note = Note.objects.create(
            title='Заметка 1',
            text='Тело заметки 1',
            slug='note1',
            author=cls.author,)

    def test_public_availability(self):
        """
        Проверяем, что нужные страницы доступны анонимному пользователю:
        главаная страница, регистрация, вход, уведомление о выходе.
        """
        cli = self.client
        urls = (f'{notes}:home', 'users:signup', 'users:login',  # noqa: E231
                'users:logout')

        for path_name in urls:
            with self.subTest(page=path_name):
                url = reverse(path_name)
                response = cli.get(url)
                self.assertTrue(response.status_code == HTTPStatus.OK)

    def test_public_redirection(self):
        """
        Проверяем, что при заходе анонимного пользователя на данные страницы
        происходит редирект на login:
            все операции с заметками, включая list.
        """
        cli = self.client
        urls = (
            (f'{notes}:add', None),  # noqa: E231
            (f'{notes}:list', None),  # noqa: E231
            (f'{notes}:success', None),  # noqa: E231
            (f'{notes}:edit', (self.note.slug,)),  # noqa: E231
            (f'{notes}:detail', (self.note.slug,)),  # noqa: E231
            (f'{notes}:delete', (self.note.slug,)),  # noqa: E231
        )

        login_url = settings.LOGIN_URL

        for path_name, params in urls:
            with self.subTest(page=path_name, params=','.join(params) if params else None):
                url = reverse(path_name, args=params)
                response = cli.get(url)
                redirect_url = f'{login_url}?next={url}'
                self.assertRedirects(response, redirect_url)


class RoutesAuthorizedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = User.objects.create(username='Автор 1')
        cls.author2 = User.objects.create(username='Автор 2')
        cls.note11 = Note.objects.create(
            title='Заметка 1',
            text='Тело заметки 1 пользователя 1',
            slug='note11',
            author=cls.author1)
        cls.note12 = Note.objects.create(
            title='Заметка 2',
            text='Тело заметки 2 пользователя 1',
            slug='note12',
            author=cls.author1)
        cls.note21 = Note.objects.create(
            title='Заметка 1',
            text='Тело заметки 1 пользователя 2',
            slug='note21',
            author=cls.author2)
        cls.note22 = Note.objects.create(
            title='Заметка 2',
            text='Тело заметки 2 пользователя 2',
            slug='note22',
            author=cls.author2)

    def test_user_can_work_with_own_notes(self):
        """
        Проверяем, что пользователь может работать
        только со своими заметками.
        """
        cli = self.client
        urls = (
            (f'{notes}:edit', (self.note11.slug,),  # noqa: E231
                cli.post, self.author1, HTTPStatus.OK),
            (f'{notes}:detail', (self.note11.slug,),  # noqa: E231
                cli.get, self.author1, HTTPStatus.OK),
            (f'{notes}:delete', (self.note11.slug,),  # noqa: E231
                cli.post, self.author1, HTTPStatus.FOUND),
            (f'{notes}:edit', (self.note22.slug,),  # noqa: E231
                cli.post, self.author1, HTTPStatus.NOT_FOUND),
            (f'{notes}:detail', (self.note22.slug,),  # noqa: E231
                cli.get, self.author1, HTTPStatus.NOT_FOUND),
            (f'{notes}:delete', (self.note22.slug,),  # noqa: E231
                cli.post, self.author1, HTTPStatus.NOT_FOUND),
        )

        for path_name, params, verb, user, status_code in urls:
            cli.force_login(user)
            with self.subTest(user=user, path_name=path_name, params=params):
                url = reverse(path_name, args=params)
                respone = verb(url)
                self.assertEqual(respone.status_code, status_code)
