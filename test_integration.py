import unittest
import urllib
import app
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, MoveTargetOutOfBoundsException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import sys
import os
import time

import pandas

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'tmp_data')

class SampleTestCase(unittest.TestCase):
    """Test that the website shows the proper things"""
    def setUp(self):
        if "SAUCE_USERNAME" in os.environ:
            self.on_sauce = True
            username = os.environ["SAUCE_USERNAME"]
            access_key = os.environ["SAUCE_ACCESS_KEY"]
            command_executor = "http://{}:{}@ondemand.saucelabs.com:80/wd/hub".format(username, access_key)
            capabilities = {}
            capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
            capabilities["platform"] = "Mac OS X 10.9"
            capabilities["browserName"] = "chrome"
            capabilities["version"] = "48"
            self.driver = webdriver.Remote(desired_capabilities=capabilities, command_executor=command_executor)
            self.action_chains = ActionChains(self.driver)
        else:
            self.on_sauce = False
            # Reference http://elementalselenium.com/tips/2-download-a-file
            new_profile = FirefoxProfile()
            new_profile.default_preferences['browser.download.dir'] = DOWNLOAD_DIR
            new_profile.default_preferences['browser.download.folderList'] = 2
            new_profile.default_preferences['browser.helperApps.neverAsk.saveToDisk'] = 'text/csv'
            self.driver = webdriver.Firefox(firefox_profile=new_profile)
            #self.driver.set_window_size(2024,1768)
            self.action_chains = ActionChains(self.driver)

        self.client = app.app.test_client()

    def tearDown(self):
        # clear the database
        self.driver.quit()
        if not "SAUCE_USERNAME" in os.environ:
            self.clear_dir(DOWNLOAD_DIR)

    def clear_dir(self, dir_to_clear):
        for output_file in os.listdir(dir_to_clear):
            os.remove(os.path.join(dir_to_clear, output_file))

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

    def mouse_out(self, element):
        window_size_x = self.driver.get_window_size()['width']
        window_size_y = self.driver.get_window_size()['height']
        position_x, position_y = element.location['x'], element.location['y']
        x_offset, y_offset = 300,300
        if window_size_x < position_x + 300:
            x_offset = -300
        if window_size_y < position_y + 300:
            y_offset = -300
        self.action_chains.move_by_offset(x_offset, y_offset)
        self.action_chains.perform()

    def test_front_page(self):
        url = "http://localhost:5000/"
        self.driver.get(url)
        assert self.driver.current_url == url

        assert self.is_text_present("Functional")
        self.driver.find_element(by=By.ID, value='link_to_functional').click()
        time.sleep(1)
        assert self.driver.current_url == url + 'functional_table'


        self.driver.get(url)
        assert self.driver.current_url == url

        assert self.is_text_present("Taxonomy")
        self.driver.find_element(by=By.ID, value='link_to_taxonomic').click()
        assert self.driver.current_url == url + 'taxonomy_table'

    def test_filtering_search(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        # Verify the accordion unfolding
        filter_search_text = "Filter by a search term"
        assert not self.is_text_present(filter_search_text)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()

        time.sleep(0.3) # The accordion takes some time to unfold

        assert self.is_text_present(filter_search_text)

        # Verify the search term filtering
        self.find_by_value(value="filter_with_search")[0].click()
        self.driver.find_element(by=By.ID, value='search_annotations').send_keys("glycosyl hydro")
        time.sleep(2) # wait for search result to load
        self.driver.execute_script("window.scrollTo(0,400)")
        assert self.is_text_present("Showing 4 out of 4 in total")

        self.driver.find_element(by=By.ID, value='submit_view').click()

        time.sleep(2) # wait for page to reload with new result
        # There are only six of these which is present as annotations
        # in the test result
        rpkm_tbody = self.driver.find_elements(by=By.CLASS_NAME, value='rpkm_values_tbody')[0]
        assert len(rpkm_tbody.find_elements(by=By.TAG_NAME, value= 'tr')) == 4 # only showing the filtered rows

    def test_filtering_type_identifier(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        # Verify the type identifiers filtering
        self.find_by_value("filter_with_type_identifiers")[0].click()
        self.driver.find_element(by=By.ID, value='type_identifiers-0').send_keys('PF00535')

        self.driver.find_element(by=By.ID, value='submit_view').click()
        time.sleep(1) # The accordion takes some time to unfold
        assert self.is_text_present("PF00535")
        rpkm_tbody = self.driver.find_elements(by=By.CLASS_NAME, value='rpkm_values_tbody')[0]
        assert len(rpkm_tbody.find_elements(by=By.TAG_NAME, value='tr')) == 1

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(by=By.ID, value='type_identifiers-1')
        self.driver.find_element(by=By.ID, value='AddAnotherTypeIdentifier').click()
        self.driver.find_element(by=By.ID, value='type_identifiers-1').send_keys('TIGR01420')

        self.driver.find_element(by=By.ID, value='submit_view').click()
        assert "PF00535" in self.driver.find_elements(by=By.TAG_NAME, value='table')[0].text
        assert "TIGR01420" in self.driver.find_elements(by=By.TAG_NAME, value='table')[0].text
        rpkm_tbody = self.driver.find_elements(by=By.CLASS_NAME, value='rpkm_values_tbody')[0]
        assert len(rpkm_tbody.find_elements(by=By.TAG_NAME, value='tr')) == 2

    def test_annotation_information(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        element = self.driver.find_elements(by=By.LINK_TEXT, value='6.1.1.4')[0]
        self.mouse_over(element)
        time.sleep(1)
        assert self.is_text_present("Leucine--tRNA ligase")

        self.mouse_out(element)
        time.sleep(1)
        assert not self.is_text_present("Leucine--tRNA ligase")

        self.driver.find_element(by=By.ID, value='toggle_description_column').click()
        time.sleep(1)
        assert self.is_text_present("Leucine--tRNA ligase")

        self.driver.find_element(by=By.ID, value='toggle_description_column').click()
        time.sleep(1)
        assert not self.is_text_present("Leucine--tRNA ligase")



    def test_show_sample_information(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)
        self.driver.find_elements(by=By.LINK_TEXT, value="Table")[0].click()

        assert not self.is_text_present("2012-08-06")
        assert not self.is_text_present("17.06204")
        element = self.driver.find_elements(by=By.LINK_TEXT, value='120806')[0]
        self.mouse_over(self.driver.find_elements(by=By.LINK_TEXT, value='120806')[0])
        time.sleep(1)
        assert self.is_text_present("2012-08-06")
        assert self.is_text_present("17.06204")

        self.mouse_out(element)
        time.sleep(1)

        assert not self.is_text_present("2012-08-06")
        assert not self.is_text_present("17.06204")

        self.driver.find_element(by=By.ID, value='toggle_sample_description').click()
        time.sleep(1)

        assert self.is_text_present("2012-08-06")
        assert self.is_text_present("17.06204")

        self.driver.find_element(by=By.ID, value='toggle_sample_description').click()
        time.sleep(1)
        assert not self.is_text_present("2012-08-06")
        assert not self.is_text_present("17.06204")

    def test_filter_samples(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        self.driver.find_elements(by=By.LINK_TEXT, value="Table")[0].click()

        # This sample should disappear after filtering
        assert self.is_text_present("120717")
        assert self.is_text_present("120802")
        assert self.is_text_present("120806")

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        select_sample = Select(self.driver.find_element(by=By.ID, value='select_sample_groups'))
        select_sample.select_by_visible_text("redox")

        self.driver.find_element(by=By.ID, value='submit_view').click()
        self.driver.find_elements(by=By.LINK_TEXT, value="Table")[0].click()
        assert self.is_text_present("P2236_101")
        assert self.is_text_present("P2236_102")
        assert self.is_text_present("P2236_103")
        assert self.is_text_present("P2236_104")
        assert not self.is_text_present("120717")
        assert not self.is_text_present("120802")
        assert not self.is_text_present("120806")

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        select_sample = Select(self.driver.find_element(by=By.ID, value='select_sample_groups'))

        # This should not unselect redox
        select_sample.select_by_visible_text("lmo")

        self.driver.find_element(by=By.ID, value='submit_view').click()
        self.driver.find_elements(by=By.LINK_TEXT, value="Table")[0].click()
        assert self.is_text_present("P2236_101")
        assert self.is_text_present("P2236_102")
        assert self.is_text_present("P2236_103")
        assert self.is_text_present("P2236_104")
        assert self.is_text_present("120717")
        assert self.is_text_present("120802")
        assert self.is_text_present("120806")


    def test_download_gene_list(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold


        self.driver.find_element(by=By.ID, value="submit_download").click()
        # Don't know how to reach files located on the sauce machine
        # This test will only verify that the button exists on sauce.
        if not self.on_sauce:
            time.sleep(3)

            gene_list = os.path.join(DOWNLOAD_DIR, 'gene_list.csv')
            assert os.path.isfile(gene_list)
            df = pandas.read_table(gene_list, sep=',', header=None, names=['gene_name', 'type_identifier'])
            print(len(df))
            assert len(df) == 76
            assert len(df.columns) == 2
            assert len(df['type_identifier'].unique()) == 20
            assert df.ix[0]['gene_name'] == 'k99_10000918_2'
            assert df.ix[0]['type_identifier'] == 'PF01609'

    def test_download_annotation_counts(self):
        url = "http://localhost:5000/functional_table"
        self.driver.get(url)

        self.driver.find_element(by=By.ID, value="filter_accordion").click()
        time.sleep(1) # The accordion takes some time to unfold

        select_what_to_download = Select(
                self.driver.find_element(by=By.ID, value='download_select')
                )

        time.sleep(1)
        select_what_to_download.select_by_visible_text("Annotation Counts")
        time.sleep(1)

        self.driver.find_element(by=By.ID, value="submit_download").click()
        time.sleep(3)

        output_file = os.path.join(DOWNLOAD_DIR, 'annotation_counts.csv')
        assert os.path.isfile(output_file)
        df = pandas.read_table(output_file, sep=',')
        assert len(df) == 20
        assert len(df.columns) == 4
        assert len(df['annotation_id'].unique()) == 20
        assert df.ix[0]['annotation_id'] == '6.1.1.4'

    def test_taxonomy_table_row_limit(self):
        url = "http://localhost:5000/taxonomy_table"
        self.driver.get(url)

        rpkm_tbody = self.driver.find_elements(by=By.CLASS_NAME, value='rpkm_values_tbody')[0]
        assert len(rpkm_tbody.find_elements(by=By.TAG_NAME, value= 'tr')) == 4 # only showing the superkingdoms

        row_limit_and_result = [("20", 20), ("50", 50), ("100", 100), ("Show All", 127)]
        for row_limit, result in row_limit_and_result:
            self.driver.get(url)
            self.driver.find_elements(by=By.LINK_TEXT, value="Table")[0].click()
            self.driver.find_element(by=By.ID, value="toggle_select_all").click()
            time.sleep(0.1)

            select_level = Select(
                    self.driver.find_element(by=By.ID, value="taxon_level_select")
                    )
            select_level.select_by_visible_text("species")
            if row_limit != "20": # 20 is the default row limit
                select_row_limit = Select(
                        self.driver.find_element(by=By.ID, value="row_limit_select")
                        )
                select_row_limit.select_by_visible_text(row_limit)

                self.driver.execute_script("window.scrollTo(0,0)")

            self.driver.find_element(by=By.ID, value='updateTaxonTable').click()
            time.sleep(1)

            rpkm_tbody = self.driver.find_elements(by=By.CLASS_NAME, value='rpkm_values_tbody')[0]
            assert len(rpkm_tbody.find_elements(by=By.TAG_NAME, value= 'tr')) == result # showing all allowed by the row limit

