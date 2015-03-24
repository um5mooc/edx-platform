"""
Course wiki
"""

from bok_choy.page_object import PageObject
from .course_page import CoursePage
from ...pages.studio.utils import type_in_codemirror


class CourseWikiPage(CoursePage):
    """
    Course wiki navigation and objects.
    """

    url_path = "course_wiki"

    def is_browser_on_page(self):
        """
        Browser is on the wiki page if the wiki breadcrumb is present
        """
        return self.q(css='.breadcrumb').present

    def open_editor(self):
        """
        Replace content of a wiki article with new content
        """
        edit_button = self.q(css='.fa-pencil')
        edit_button.click()

    @property
    def article_name(self):
        """
        Return the name of the article
        """
        return str(self.q(css='.main-article h1').text[0])


class CourseWikiEditPage(PageObject):
    """
    Editor page
    """
    url = None

    def is_browser_on_page(self):
        """
        The wiki page editor
        """
        return self.q(css='.CodeMirror-scroll').present

    def replace_wiki_content(self, content):
        """
        Editor must be open already. This will replace any content in the editor
        with new content
        """
        type_in_codemirror(self, 0, content)

    def save_wiki_content(self):
        """
        When the editor is open, click save
        """
        self.q(css='button[name="save"]').click()
        self.wait_for_element_presence('.alert-success', 'wait for the article to be saved')
