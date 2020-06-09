#!/usr/bin/env python3
import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
import sys

# Set-up the logger.
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S',
                    level=logging.INFO)


def ask_user(question: str) -> str:
    resp = None
    while not resp:
        resp = input(question)
    return resp


def login(driver: WebDriver, username: str, password: str):
    # Load Minerva home.
    driver.get('https://minerva.ugent.be/')

    # Click the login button.
    login_btn = driver.find_element_by_id('btn_logincas')
    login_btn.click()
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'login.ugent.be' in d.current_url)

    # Fill in username.
    username_field = driver.find_element_by_id('username')
    username_field.send_keys(username)

    # Fill in password.
    password_field = driver.find_element_by_id('user_pass')
    password_field.send_keys(password)

    # Click authenticate button.
    login_auth_btn = driver.find_element_by_id('wp-submit')
    login_auth_btn.click()
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'minerva.ugent.be' in d.current_url)


def get_courses(driver: WebDriver) -> set:
    driver.get("https://minerva.ugent.be/main/curriculum/index.php?year=2019")
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: 'curriculum' in d.current_url)

    # Get the courses.
    courses = set()
    links = driver.find_elements_by_tag_name('a')
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'course_home.php?cidReq=' in href:
            courses.add(link.get_attribute('href'))

    return courses


def download(driver: WebDriver, course: str):
    # Browse to the home directory.
    driver.get(course)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: course in d.current_url)

    files = course.replace("course_home", "document")
    driver.get(files)
    sleep = WebDriverWait(driver, 10)
    sleep.until(lambda d: files in d.current_url)

    # Click the zip link.
    links = driver.find_elements_by_tag_name('a')
    ziplink = None
    for link in links:
        href = link.get_attribute('href')
        if href is not None and 'downloadfolder' in href:
            ziplink = href
            break

    if not ziplink:
        logging.error("ZIP-link not found :(")
        exit(1)

    # Determine the course name.
    course_name = None
    for c in driver.find_elements_by_tag_name('h1'):
        if 'minerva' not in str(c.text).lower():
            course_name = c.text

    # Find the file name.
    course_name_clean = "".join(c for c in course_name if
                                c.isalpha() or c.isdigit() or c == ' ').rstrip()
    new_name = f"{course[course.index('cidReq') + 7:]} - {course_name_clean.lower()}.zip"

    if os.path.exists(os.path.join(out_dir, new_name)):
        logging.info(f"Already exists {new_name}")
        return

    driver.get(ziplink)

    # Wait for the file to download.
    logging.info("Awaiting file download...")
    out_file = os.path.join(out_dir, 'documents.zip')
    sleep = WebDriverWait(driver, 1800)
    sleep.until(lambda d: os.path.exists(out_file))

    # Rename the file.
    os.rename(out_file, os.path.join(out_dir, new_name))
    logging.info(f"Saved {new_name}")


if __name__ == '__main__':
    # Validate arguments.
    if len(sys.argv) != 2:
        logging.error("Syntax: python3 main.py output_directory")
        exit(1)

    # Parse arguments.
    out_dir = os.path.abspath(sys.argv[1]).rstrip("/") + "/"

    # Get username from user.
    username = ask_user("Username?")
    password = ask_user("Password?")

    # Create a new webdriver.
    logging.info("Booting...")
    prefs = {"download.default_directory": out_dir}

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(executable_path="./chromedriver",
                              chrome_options=options)

    logging.info("Authenticating...")
    login(driver, username, password)

    logging.info("Getting courses...")
    courses = get_courses(driver)

    logging.info(f"Found {len(courses)} courses.")

    for ci, course in enumerate(courses):
        logging.info(f"Downloading {ci + 1}/{len(courses)}")
        download(driver, course)

    logging.info("Done!")
