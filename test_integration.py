import unittest
import urllib
import app
import splinter
from splinter import Browser

import sys

import time

class SampleTestCase(unittest.TestCase):
    """Test that the website shows the proper things"""
    def setUp(self):
        self.db = app.db
        self.db.create_all()
        self.client = app.app.test_client()

    def tearDown(self):
        # clear the database
        self.db.drop_all()

    def test_get_base(self):
        r = self.client.get('/')
        assert r._status_code == 200
        assert b'Baltic Sea Reference Metagenome' in r.data

        assert b'Function Classes' in r.data

    def test_filtering_search(self):
        with Browser() as browser:
            url = "http://localhost:5000/"
            browser.visit(url)

            # Verify the accordion unfolding
            filter_search_text = "Filter by a search term"
            assert browser.is_text_not_present(filter_search_text)

            browser.find_by_id("filter_accordion").click()

            time.sleep(0.3) # The accordion takes some time to unfold

            assert browser.is_text_present(filter_search_text)

            # Verify the search term filtering
            browser.find_by_value("filter_with_search").first.click()
            browser.fill('search_annotations', "octaprenyltransferase")

            browser.execute_script("window.scrollTo(0,1000)")
            time.sleep(4) # wait for search result to load
            assert browser.is_text_present("Showing 4 out of 4 in total")

            browser.find_by_id('submit_filter').click()

            time.sleep(2) # wait for page to reload with new result
            # There are only two of these which is present as annotations
            # in the test result
            assert len(browser.find_by_tag('tr')) == 3 # only showing the filtered rows

    def test_filtering_type_identifier(self):
        with Browser() as browser:
            url = "http://localhost:5000/"
            browser.visit(url)

            browser.find_by_id("filter_accordion").click()
            time.sleep(1) # The accordion takes some time to unfold

            # Verify the type identifiers filtering
            browser.find_by_value("filter_with_type_identifiers").click()
            browser.fill('type_identifiers-0', 'pfam01027')

            browser.find_by_id('submit_filter').click()
            assert browser.is_text_present("pfam01027")
            assert len(browser.find_by_tag('tr')) == 2

            browser.find_by_id("filter_accordion").click()
            time.sleep(1) # The accordion takes some time to unfold

            with self.assertRaises(splinter.exceptions.ElementDoesNotExist):
                browser.fill('type_identifiers-1', 'TIGR01320')
            browser.find_by_id('AddAnotherTypeIdentifier').click()
            browser.fill('type_identifiers-1', 'TIGR03634')

            browser.find_by_id('submit_filter').click()
            assert "pfam01027" in browser.find_by_tag('table').first.html
            assert "TIGR03634" in browser.find_by_tag('table').first.html
            assert len(browser.find_by_tag('tr')) == 3

    def test_annotation_information(self):
        with Browser() as browser:
            url = "http://localhost:5000/"
            browser.visit(url)

            browser.find_by_text('pfam02518').first.mouse_over()
            time.sleep(1)
            assert browser.is_text_present("Histidine kinase-, DNA gyrase B-, and HSP90-like ATPase.")

            browser.find_by_tag('td').first.mouse_out()
            time.sleep(1)
            assert not browser.is_text_present("Histidine kinase-, DNA gyrase B-, and HSP90-like ATPase. ")

            browser.find_by_id('toggle_description_column').click()
            time.sleep(1)
            assert browser.is_text_present("Histidine kinase-, DNA gyrase B-, and HSP90-like ATPase.")

            browser.find_by_id('toggle_description_column').click()
            time.sleep(1)
            assert not browser.is_text_present("Histidine kinase-, DNA gyrase B-, and HSP90-like ATPase. ")
