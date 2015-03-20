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

    def edit_article(self, content):
        edit_button = self.q(css='.fa-pencil')
        text_edit_box = self.q(css='.CodeMirror-cursor')
        edit_button.click()
        self.wait_for_element_presence('.CodeMirror-scroll', 'wait for wiki edit screen')

        type_in_codemirror(self, 0, content)
        self.q(css='button[name="save"]').click()
        self.wait_for_element_presence('.alert-success', 'wait for the article to be saved')



    @property
    def article_name(self):
        """
        Return the name of the article
        """
        return str(self.q(css='.main-article h1').text[0])


