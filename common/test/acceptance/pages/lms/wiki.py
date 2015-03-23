"""
Course wiki
"""

from bok_choy.page_object import PageObject
from ...pages.studio.utils import type_in_codemirror


class CourseWikiPage(PageObject):
    """
    Course wiki navigation and objects.
    """

    url = None

    def is_browser_on_page(self):
        """
        Browser is on the wiki page if the wiki breadcrumb is present
        """
        return self.q(css='.breadcrumb').present

    def confirm_editor_open(self):
        """
        The wiki page editor. Raise an error if it is not open.
        """
        return self.q(css='.CodeMirror-scroll').present

    def open_editor(self):
        """
        Replace content of a wiki article with new content
        """
        edit_button = self.q(css='.fa-pencil')
        edit_button.click()
        self.wait_for(self.confirm_editor_open, 'Wait for editor to open')

    def replace_wiki_content(self, content):
        """
        Editor must be open already. This will replace any content in the editor
        with new content
        """
        self.confirm_editor_open
        type_in_codemirror(self, 0, content)

    def save_wiki_content(self):
        """
        When the editor is open, click save
        """
        self.confirm_editor_open
        self.q(css='button[name="save"]').click()
        self.wait_for_element_presence('.alert-success', 'wait for the article to be saved')

    @property
    def article_name(self):
        """
        Return the name of the article
        """
        return str(self.q(css='.main-article h1').text[0])
