import unittest
import urllib
import app
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

import sys
import os
import time

class SampleTestCase(unittest.TestCase):
    """Test that the website shows the proper things"""
    def setUp(self):
        if "SAUCE_USERNAME" in os.environ:
            username = os.environ["SAUCE_USERNAME"]
            access_key = os.environ["SAUCE_ACCESS_KEY"]
            command_executor = "http://{}:{}@ondemand.saucelabs.com:80/wd/hub".format(username, access_key)
            capabilities = {}
            capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
            self.driver = webdriver.Remote(desired_capabilities=capabilities, command_executor=command_executor)
            self.action_chains = ActionChains(self.driver)
        else:
            self.driver = webdriver.Firefox()
            self.action_chains = ActionChains(self.driver)
        self.db = app.db
        self.db.create_all()
        self.client = app.app.test_client()

    def tearDown(self):
        # clear the database
        self.db.drop_all()
        self.driver.quit()

    def is_text_present(self, text):
        body_text = self.driver.find_element(By.TAG_NAME, "body").text
        return text in body_text

    def find_by_value(self, value):
        elements = self.driver.find_elements(By.XPATH, '//*[@value="%s"]' % value)
        return elements

    def mouse_over(self, element):
        """
        Performs a mouse over the element.
        Currently works only on Chrome driver.
        """
        self.action_chains.move_to_element(element)
        self.action_chains.perform()

    def mouse_out(self):
        self.action_chains.move_by_offset(5000, 5000)
        self.action_chains.perform()

    def test_get_base(self):
        r = self.client.get('/')
        assert r._status_code == 200
        assert b'Baltic Sea Reference Metagenome' in r.data

        assert b'Function Classes' in r.data

    def test_filtering_search(self):
        url = "http://localhost:5000/"
        self.driver.get(url)

        # Verify the accordion unfolding
        filter_search_text = "Filter by a search term"
        assert not self.is_text_present(filter_search_text)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()

        time.sleep(0.3) # The accordion takes some time to unfold

        assert self.is_text_present(filter_search_text)

        # Verify the search term filtering
        self.find_by_value(value="filter_with_search")[0].click()
        self.driver.find_element(by=By.ID, value='search_annotations').send_keys("glycosy")
        time.sleep(2) # wait for search result to load
        self.driver.execute_script("window.scrollTo(0,400)")
        assert self.is_text_present("Showing 8 out of 8 in total")

        self.driver.find_element(by=By.ID, value='submit_filter').click()

        time.sleep(2) # wait for page to reload with new result
        # There are only six of these which is present as annotations
        # in the test result
        assert len(self.driver.find_elements(by=By.TAG_NAME, value= 'tr')) == 7 # only showing the filtered rows

    def test_filtering_type_identifier(self):
        url = "http://localhost:5000/"
        self.driver.get(url)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        # Verify the type identifiers filtering
        self.find_by_value("filter_with_type_identifiers")[0].click()
        self.driver.find_element(by=By.ID, value='type_identifiers-0').send_keys('pfam00535')

        self.driver.find_element(by=By.ID, value='submit_filter').click()
        assert self.is_text_present("pfam00535")
        assert len(self.driver.find_elements(by=By.TAG_NAME, value='tr')) == 2

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(by=By.ID, value='type_identifiers-1')
        self.driver.find_element(by=By.ID, value='AddAnotherTypeIdentifier').click()
        self.driver.find_element(by=By.ID, value='type_identifiers-1').send_keys('TIGR01420')

        self.driver.find_element(by=By.ID, value='submit_filter').click()
        assert "pfam00535" in self.driver.find_elements(by=By.TAG_NAME, value='table')[0].text
        assert "TIGR01420" in self.driver.find_elements(by=By.TAG_NAME, value='table')[0].text
        assert len(self.driver.find_elements(by=By.TAG_NAME, value='tr')) == 3

    def test_annotation_information(self):
        url = "http://localhost:5000/"
        self.driver.get(url)

        self.mouse_over(self.driver.find_elements(by=By.LINK_TEXT, value='COG0059')[0])
        time.sleep(1)
        assert self.is_text_present("Ketol-acid reductoisomerase [Amino acid transport and metabolism")

        self.mouse_out()
        time.sleep(1)
        assert not self.is_text_present("Ketol-acid reductoisomerase [Amino acid transport and metabolism")

        self.driver.find_element(by=By.ID, value='toggle_description_column').click()
        time.sleep(1)
        assert self.is_text_present("Ketol-acid reductoisomerase [Amino acid transport and metabolism")

        self.driver.find_element(by=By.ID, value='toggle_description_column').click()
        time.sleep(1)
        assert not self.is_text_present("Ketol-acid reductoisomerase [Amino acid transport and metabolism")
