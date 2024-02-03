from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notes.models import Note
# from notes.models import Note
from notes.urls import app_name as notes

User = get_user_model()


class AcessNotesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = User.objects.create(username='Автор 1')
        cls.author2 = User.objects.create(username='Автор 2')
        notes_data = [
            {
                'title': 'Заметка 1',
                'text': 'Тело заметки 1 пользователя 1',
                'slug': 'note11',
                'author': cls.author1
            },
            {
                'title': 'Заметка 2',
                'text': 'Тело заметки 2 пользователя 1',
                'slug': 'note12',
                'author': cls.author1,
            },
            {
                'title': 'Заметка 1',
                'text': 'Тело заметки 1 пользователя 2',
                'slug': 'note21',
                'author': cls.author2,
            },
            {
                'title': 'Заметка 2',
                'text': 'Тело заметки 2 пользователя 2',
                'slug': 'note22',
                'author': cls.author2
            },
        ]
        dal_objects = (Note(**item) for item in notes_data)
        Note.objects.bulk_create(dal_objects)

    def test_user_can_see_only_own_notes1(self):
        """
        Проверяем, что пользователь 1 может видеть
        только свои заметками.
        """
        cli = self.client
        url = reverse(f'{notes}:list')  # noqa: E231

        cli.force_login(self.author1)
        response = cli.get(url)

        note_objects = response.context['note_list']
        self.assertEqual(note_objects.count(), 2)
        self.assertEqual(note_objects[0].slug, 'note11')
        self.assertEqual(note_objects[1].slug, 'note12')

    def test_user_can_see_only_own_notes2(self):
        """
        Проверяем, что пользователь 2 может видеть
        только свои заметками.
        """
        cli = self.client
        url = reverse(f'{notes}:list')  # noqa: E231

        cli.force_login(self.author2)
        response = cli.get(url)

        note_objects = response.context['note_list']
        self.assertEqual(note_objects.count(), 2)
        self.assertEqual(note_objects[0].slug, 'note21')
        self.assertEqual(note_objects[1].slug, 'note22')

    def test_user_can_see_only_own_notes1(self):
        """Проверяем, что заметки отсртированы по id ASC."""
        cli = self.client
        url = reverse(f'{notes}:list')  # noqa: E231

        cli.force_login(self.author1)
        response = cli.get(url)

        note_objects = response.context['note_list']
        all_note_slugs = [n.slug for n in note_objects]
        sorted_notes = sorted(all_note_slugs)
        self.assertEqual(all_note_slugs, sorted_notes)
