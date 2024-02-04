import inspect
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from notes.models import Note
from notes.urls import app_name as notes

User = get_user_model()

NOTE_FIELDS = ('title', 'text', 'slug', 'author')


def clone_model_fields(data):
    return {key: value
            for key, value in inspect.getmembers(data)
            if key in NOTE_FIELDS}


class NoteCreationAndValidationTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.anonimous_client = Client()
        cls.user = User.objects.create(username='User1')
        cls.auth_client = Client()
        cls.auth_client.force_login(cls.user)
        cls.url_add = reverse(f'{notes}:add')  # noqa: E231

    def test_unique_title(self):
        """Обеспечена уникальность title."""
        self.auth_client.post(self.url_add, data={
            'title': 'Новое в оплате метро',
            'text': 'С января вводится проход в метро с оплатой мобильным.',
            'slug': 'metro_new_pay_method',
            'author': self.user,
        })

        rsp = self.auth_client.post(self.url_add, data={
            'title': 'Открыта станция на Люблинской линии',
            'text': 'С февраля появится новая станция на Люблинской линии.',
            'slug': 'metro_new_pay_method',
            'author': self.user,
        })

        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Note.objects.all()[0].slug, 'metro_new_pay_method')
        self.assertFormError(
            rsp,
            form='form',
            field='slug',
            errors=('metro_new_pay_method - такой slug уже существует, '
                    'придумайте уникальное значение!')
        )

    def test_slug_filling(self):
        """Если slig пришёл в форме пустой, то он заполняется из title
        по правиласм с усечением.
        """
        self.auth_client.post(self.url_add, data={
            'title': 'Новое в оплате метро',
            'text': 'С января вводится проход в метро с оплатой мобильным.',
            'author': self.user,
        })

        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Note.objects.all()[0].slug, 'novoe-v-oplate-metro')

    def test_mandatory_text(self):
        """Поле text обязательное"""
        rsp = self.auth_client.post(self.url_add, data={
            'title': 'Новое в оплате метро',
            'author': self.user,
        })
        self.assertEqual(Note.objects.count(), 0)
        self.assertFormError(
            rsp,
            form='form',
            field='text',
            errors='Обязательное поле.'
        )

    def test_mandatory_title(self):
        """Поле title обязательное"""
        rsp = self.auth_client.post(self.url_add, data={
            'text': 'Новое в оплате метро',
            'author': self.user,
        })
        self.assertEqual(Note.objects.count(), 0)
        self.assertFormError(
            rsp,
            form='form',
            field='title',
            errors='Обязательное поле.'
        )

    def test_anonimous_cant_create_note(self):
        """Анонимный пользователь не может создать заметку"""
        self.anonimous_client.post(self.url_add, data={
            'title': 'Новое в оплате метро',
            'text': 'С января вводится проход в метро с оплатой мобильным.',
            'author': self.user,
        })

        self.assertEqual(Note.objects.count(), 0)

    def test_authorized_can_create_note(self):
        """Залогиненный пользователь может создать заметку"""
        self.auth_client.post(self.url_add, data={
            'title': 'Новое в оплате метро',
            'text': 'С января вводится проход в метро с оплатой мобильным.',
            'author': self.user,
        })

        self.assertEqual(Note.objects.count(), 1)


class NoteModificationTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create(username='User1')
        cls.user2 = User.objects.create(username='User2')
        cls.client1 = Client()
        cls.client2 = Client()
        cls.client1.force_login(cls.user1)
        cls.client2.force_login(cls.user2)

        cls.note1 = Note(
            title='Заметка 1',
            text='Тело заметки 1 пользователя 1',
            slug='note21',
            author=cls.user1,
        )
        cls.note1.save()
        cls.note2 = Note(
            title='Заметка 2',
            text='Тело заметки 2 пользователя 2',
            slug='note22',
            author=cls.user2,
        )
        cls.note2.save()
        cls.success_url = reverse(f'{notes}:success')  # noqa: E231

    def test_authorized_can_edit_own_note(self):
        """Пользователь может редактировать свои заметки."""
        url_edit = reverse(f'{notes}:edit',  # noqa: E231
                           args=(self.note1.slug,))

        form_data = clone_model_fields(self.note1)

        form_data['text'] = '---123---'
        rsp = self.client1.post(url_edit, data=form_data)
        self.assertRedirects(rsp, self.success_url)
        fresh_data = Note.objects.get(pk=self.note1.id)
        self.assertEqual(fresh_data.text, form_data['text'])

    def test_authorized_cant_edit_else_note(self):
        """Пользователь не может редактировать чужие заметки."""
        url_edit = reverse(f'{notes}:edit',  # noqa: E231
                           args=(self.note2.slug,))

        form_data = clone_model_fields(self.note2)

        old_text = form_data['text']
        form_data['text'] = '---123---'
        rsp = self.client1.post(url_edit, data=form_data)
        self.assertEqual(rsp.status_code, HTTPStatus.NOT_FOUND)
        fresh_data = Note.objects.get(pk=self.note2.id)
        self.assertEqual(fresh_data.text, old_text)

    def test_authorized_can_delete_own_note(self):
        """Пользователь может удалять свои заметки."""
        url_del = reverse(f'{notes}:delete',  # noqa: E231
                          args=(self.note1.slug,))
        rsp = self.client1.post(url_del)
        self.assertRedirects(rsp, self.success_url)
        self.assertEqual(Note.objects.count(), 1)

    def test_authorized_cant_delete_else_note(self):
        """Пользователь не может удалять чужие заметки."""
        url_del = reverse(f'{notes}:delete',  # noqa: E231
                          args=(self.note2.slug,))
        rsp = self.client1.post(url_del)
        self.assertEqual(rsp.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Note.objects.count(), 2)
