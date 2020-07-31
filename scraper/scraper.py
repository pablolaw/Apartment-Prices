import os
import sys
from getopt import getopt

import time
from datetime import datetime
from random import randint
import csv
import argparse
from dateutil.parser import parse
from re import sub, search
from urllib.parse import urlparse, parse_qs
import json
import pdb
from copy import deepcopy

import selenium
from selenium import webdriver, common
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, \
     NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from geocoder import get_coordinates
from notifier import send_message, notify_error


BASE_URL = 'https://www.padmapper.com/apartments/toronto-on?exclude-airbnb'
MAX_LISTINGS = 7400
AMENITIES = {
    'Balcony': 0,
    'Dishwasher': 0,
    'In Unit Laundry': 0,
    'On Site Laundry': 0,
    'Assigned Parking': 0,
    'Fitness Center': 0,
    'Garage Parking': 0,
    'Storage': 0,
    'Concierge Service': 0,
    'Swimming Pool': 0
}
ATTRS = ['lng',
         'lat',
         'Bedrooms',
         'Bathrooms',
         'Size',
         'Balcony',
         'Dishwasher',
         'In Unit Laundry',
         'On Site Laundry',
         'Assigned Parking',
         'Fitness Center',
         'Garage Parking',
         'Storage',
         'Concierge Service',
         'Swimming Pool',
         'Price'
]


def jump_to(href):
    url = href if 'http' in href else (BASE_URL + href)
    # print("+ Jumping to {}".format(url))
    driver.get(url)

def find_and_click(id):
    driver.find_element_by_css_selector('#{}'.format(id)).click()

def wait_for_nested_element(element, selector, sec=30):
    wait = WebDriverWait(element, sec)
    return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

def wait_for(selector, sec=30):
    wait = WebDriverWait(driver, sec)
    return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

def set_defaults():
    all_prices = 'ctl00_ContentPlaceHolder1_ucSearchDetails1_chkPriceAll'
    all_furnishing = 'ctl00_ContentPlaceHolder1_ucSearchDetails1_chkFurnishedAll'
    find_and_click(all_prices)
    wait_for('#{}'.format(all_furnishing))
    find_and_click(all_furnishing)

def jump_to_listings_for(num_bedrooms, zone):
    jump_site = 'http://www.viewit.ca/vwListings.aspx?bedrooms={}&CID={}'.format(num_bedrooms, zone)
    jump_to(jump_site)

def parse_to_int(attr_str, sqft=False):
    if sqft and attr_str == '—':
        return None
    try:
        if search('K', attr_str) is not None:
            return float(sub(r'[^\d.]', '', attr_str))*1000
        return int(sub(r'[^\d.]', '', attr_str))
    except ValueError:
        print(f'Found an unparseable attribute string: {attr_str}, sqft={sqft}')
        return None

def get_bedrooms(room_element):
    bedroom_str = room_element.find_element_by_class_name('Floorplan_title__179XB').text
    if bedroom_str == "Studios":
        num_beds = 0
    else:
        num_beds = int(bedroom_str[0])
    # Check if listing has a den
    den_ind = room_element.find_element_by_class_name('Floorplan_floorplanTitle__3iB55').text
    match = search(r'.+\s[dD]en.*', den_ind)
    if match is not None:
        num_beds += 0.5
    return num_beds

def scrape_address():
    info_tbl = driver.find_element_by_class_name('SummaryTable_summaryTable__3zCmu')
    address = info_tbl.find_elements_by_tag_name('li')[-3].find_element_by_tag_name('div').text
    return address

def get_multiple_listings(attr_dict):
    wait_for('.Floorplan_floorplansContainer__2Rtwg', 2) # Raises TimeoutException
    bed_list = driver.find_elements_by_class_name('Floorplan_floorplansContainer__2Rtwg')
    listings = []
    for room_type in bed_list:
        room_type.find_element_by_class_name('Floorplan_floorplanPanel__25nE5').click()
        try:
            wait_for_nested_element(room_type, '.Floorplan_specLabel__1ZbKH', 2)
            room_price = room_type.find_element_by_class_name('Floorplan_floorplanPrice__230Qt')
            room_comp = room_type.find_elements_by_class_name('Floorplan_specLabel__1ZbKH')
            room_attr = {
                'Bedrooms': get_bedrooms(room_type),
                'Bathrooms': parse_to_int(room_comp[1].text),
                'Size': parse_to_int(room_comp[0].text, sqft=True),
                'Price': parse_to_int(room_price.text)
            }
            attr_dict_cpy = deepcopy(attr_dict)
            attr_dict_cpy.update(room_attr)
            listings.append(attr_dict_cpy)
        except TimeoutException:
            pass
    return listings

def get_single_listing(attr_dict):
    room_comp_panel = driver.find_element_by_class_name('BubbleDetail_listingAmenities__37Cvp')
    room_comp = room_comp_panel.find_elements_by_class_name('BubbleDetail_imageText__33oD_')
    room_price = driver.find_element_by_class_name('BubbleDetail_colPrice__2mVzj').text
    if search('STUDIO(S{0,1})|Studio(s{0,1})|Bachelor|ROOM', room_comp[0].text) is not None:
        num_beds = 0
    else:
        num_beds = parse_to_int(room_comp[0].text)
    room_attr = {
            'Bedrooms': num_beds,
            'Bathrooms': parse_to_int(room_comp[1].text),
            'Size': parse_to_int(room_comp[4].text, sqft=True),
            'Price': parse_to_int(room_price)
    }
    attr_dict_cpy = deepcopy(attr_dict)
    attr_dict_cpy.update(room_attr)
    return [attr_dict_cpy]

def get_listings(attr_dict):
    rooms = attr_dict
    try:
        rooms = get_multiple_listings(attr_dict)
        assert(isinstance(rooms, list))
        return rooms
    except TimeoutException:
        pass
    rooms = get_single_listing(attr_dict) # Raises NoSuchElementException if format is non-standard
    assert(isinstance(rooms, list))
    return rooms

def change_to_new_window():
    wait_for('.BubbleDetail_btnMoreDetail__16Qzs')
    scroll_and_click('.BubbleDetail_btnMoreDetail__16Qzs')
    driver.switch_to.window(driver.window_handles[-1])

def change_to_orig_window():
    driver.close()
    driver.switch_to.window(main_window)
    # Goes to button to the top of the page
    try:
        top_btn = driver.find_element_by_class_name('BubbleDetail_btnMsg__225HI')
        driver.execute_script("arguments[0].scrollIntoView();", top_btn)
    except NoSuchElementException:
        top_panel = driver.find_element_by_class_name('BubbleDetail_priceLocation__3xlMs')
        driver.execute_script("arguments[0].scrollIntoView();", top_panel)

def get_amenities():
    attr_dict = deepcopy(AMENITIES)
    try:
        panels = driver.find_elements_by_class_name('Amenities_amenities__w0bR_')
        for panel in panels:
            amenities = panel.find_elements_by_class_name('Amenities_text__3STBF')
            for amenity in amenities:
                if amenity.text in attr_dict.keys():
                    attr_dict[amenity.text] += 1
    except NoSuchElementException:
        pass
    finally:
        return attr_dict

def current_vit():
    parsed = urlparse(driver.current_url)
    return parse_qs(parsed.query).get('ViT', '')

def find_rental():
    price_el = 'ctl00_ContentPlaceHolder1_lblPrice'
    address_el = 'ctl00_ContentPlaceHolder1_lbNameAddress'

    try:
        address = driver.find_element_by_id(address_el).text
    except NoSuchElementException:
        address = ''

    try:
        price = driver.find_element_by_id(price_el)
        intersection = driver.find_element_by_css_selector('h1')
        posting_number = 'vit-{}'.format(current_vit()[0])

        return {
            "price": parse_price(price.text.strip()),
            "designator": posting_number,
            "address": address.strip(),
            "intersection": intersection.text.strip()
        }
    except ValueError:
        print("Found an unparseable listing price")
        return None
    except NoSuchElementException:
        return None

def check_listings():
    with open('listings.json', 'r') as listings:
        listings = json.load(listings)
    print("Retrived seen listings...")
    return listings

def save_listings():
    print(f'Collected {len(seen_listings)} listings. Saving...')
    to_file = json.dumps(seen_listings, indent=4)
    with open('listings.json', 'w') as listings:
        listings.write(to_file)
    print("Successfully saved seen listings.")


def random_sleep(minimum=0, maximum=30):
    a = randint(minimum, maximum)
    b = randint(minimum, maximum + 1)
    c = randint(minimum + 1, maximum)
    sleep_time = (a + b + c) / 3
    # print("* Sleeping for {}".format(sleep_time))
    time.sleep(sleep_time)

def short_sleep():
    random_sleep(minimum=1, maximum=3)

def long_sleep():
    random_sleep(minimum=8, maximum=30)

def check_for_existing():
    # Get canonical url
    c_url = driver.find_element_by_css_selector('[rel="canonical"]').get_attribute('href')
    if c_url not in seen_listings:
        seen_listings[c_url] = 1
        return False
    else:
        return True

def traverse(bedroom_size, zone, auto, direct_import):
    browser_log = driver.get_log('performance')
    events = [process_browser_log_entry(entry) for entry in browser_log]
    events = [event for event in events if 'Network.response' in event['method']]
    print(events)
    print(">> Checking for bedroom_size: {} in zone: {}".format(bedroom_size, zone))
    buffer = []
    has_listings = True

    short_sleep()
    jump_to_listings_for(bedroom_size, zone)
    try:
        links = driver.find_elements_by_class_name('blulink')
        links[0].click()
    except (NoSuchElementException, IndexError):
        print('<< Skipping, could not find the first listing')
        print('<< page title: {}'.format(driver.title))
        has_listings = False

    while has_listings:
        short_sleep()
        rental = find_rental()
        if rental is not None:
            print(rental)
        else:
            random_sleep(maximum=2)

        try:
            next_button = driver.find_element_by_id('ctl00_ContentPlaceHolder1_lnkNext')
            next_button.click()
        except NoSuchElementException:
            print('<< Terminating, could not find next button')
            print('<< page title: {}'.format(driver.title))
            has_listings = False

    return buffer

def debug(url):
    jump_to(url)
    print(find_rental())

def move_and_click(selector=None, element=None):
    if element is None:
        element = driver.find_element_by_css_selector(selector)
    actions = ActionChains(driver)
    actions.move_to_element(element).click().perform()

def scroll_and_click(selector=None, element=None):
    if element is None:
        element = driver.find_element_by_css_selector(selector)

    driver.execute_script("arguments[0].scrollIntoView();", element)
    short_sleep()
    element.click()

def init_writer():
    fd = open('rent_data.csv', 'w')
    with fd:
        writer = csv.DictWriter(fd, fieldnames=ATTRS)
        writer.writeheader()

def write_to_csv(attr_dicts):
    fd = open('rent_data.csv', 'a')
    with fd:
        writer = csv.DictWriter(fd, fieldnames=ATTRS)
        writer.writerows(attr_dicts)
        # print(f'Wrote {len(attr_dicts)} entries to csv.')

def main(init_csv=False):
    print(f'Beginning scraping with init_csv={init_csv}')
    jump_to('')
    driver.find_element_by_css_selector('[aria-label="Display the results in List View"]').click()
    listings_batch = 0
    pointer = 0
    if init_csv:
        init_writer()
    num_tries = 0

    # num_tries is the number of times to attempt getting reference before giving up
    while num_tries < 4 and pointer < MAX_LISTINGS:
        # Retrieve list of listings
        print(f'Getting list of listings...')
        wait_for('.ListItem_listItem__1dHWi')
        listings = driver.find_elements_by_class_name('ListItem_listItem__1dHWi')
        listings = listings[pointer:] # Take only unseen listings
        for listing in listings:
            try:
                scroll_and_click(None, listing)
            except StaleElementReferenceException:
                print(f'<< Element reference went stale. Retrieving new reference. ({pointer + listings_batch})')
                send_message("StaleElementReferenceException caught.")
                pointer += listings_batch
                num_tries += 1
                break
            listings_batch += 1
            num_tries = 0
            if (pointer + listings_batch) % 100 == 0:
                print(f'Scraped {pointer + listings_batch} listings...')
            if (pointer + listings_batch) % 1000 == 0:
                send_message(f'Scraped {pointer + listings_batch} listings.')
            try:
                change_to_new_window()
                seen = True
                try:
                    address = scrape_address()
                    seen = check_for_existing()
                except Exception:
                    pass
                finally:
                    change_to_orig_window()
                if seen:
                    # print(f'Already saw this listing: {address}. Skipping...')
                    continue
                print(f'New listing found: {address}')
                short_sleep()
                room_attrs = get_amenities()
                room_attrs.update(get_coordinates(address))
                rooms = get_listings(room_attrs)
                write_to_csv(rooms)
            except (StaleElementReferenceException, NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException, TimeoutException, ValueError):
                print(f'<< Could not retrieve listing attribute. Exiting listing ({pointer + listings_batch}).')
            finally:
                driver.execute_script("window.history.go(-1)") # Go back to last page
        pointer += listings_batch
        listings_batch = 0

    if num_tries >= 4:
        print("Unable to obtain non-stale reference to listing.")
        raise Exception
    print('DONE! Scraped {pointer} listings.')

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

if __name__ == '__main__':
    try:
        chromeOptions = webdriver.ChromeOptions()
        caps = DesiredCapabilities.CHROME
        caps['goog:loggingPrefs'] = {'performance': 'ALL'}
        prefs = {'profile.managed_default_content_settings.images': 2}
        chromeOptions.add_argument('--headless')
        chromeOptions.add_experimental_option("prefs", prefs)
        driver = webdriver.Chrome('/Users/matt/Documents/MyProjects/scraper/drivers/chromedriver', options=chromeOptions, desired_capabilities=caps)
        main_window = driver.current_window_handle
        seen_listings = check_listings()
        opts, args = getopt(sys.argv[1:], "i:")
        init_csv = False
        for opt, arg in opts:
            if opt == '-i' and arg == 'True':
                init_csv = True
        main(init_csv)
    except Exception as e:
        filename = './errors/error_{}.png'.format(datetime.now())
        print("Taking error screenshot to {}".format(filename))
        driver.save_screenshot(filename)
        notify_error(e)
        raise e
    finally:
        save_listings()
        driver.quit()
