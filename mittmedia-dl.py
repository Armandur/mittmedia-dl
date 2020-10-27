from selenium import webdriver
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.common import exceptions
import requests
import time
import os
import sys
from pathlib import Path
import shutil
from datetime import date
from PyPDF2 import PdfFileMerger
from PyPDF2 import PdfFileReader
from PyPDF2 import utils
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("email", help="Email", type=str)
parser.add_argument("password", help="Password", type=str)
parser.add_argument("secret", help="Secret (x-textalk-content-client-authorize)", type=str)
# parser.add_argument("-o", "--output", nargs=1, help="Output directory", type=str, default=os.getcwd())
parser.add_argument("-v", "--verbose", help="Verbose", action="store_true")
parser.add_argument("--not-headless", help="Don't run driver in headless mode", action="store_true")
args = parser.parse_args()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:82.0) Gecko/20100101 Firefox/82.0',
    'Accept': 'application/pdf',
    'Accept-Language': 'sv-SE,sv;q=0.8,en-US;q=0.5,en;q=0.3',
    'x-textalk-content-client-authorize': args.secret,
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}

output_path = os.getcwd()

options = Options()
if not args.not_headless:
    options.add_argument('-headless')

driver = Firefox(executable_path='geckodriver', options=options)
driver.implicitly_wait(2)

driver.get("https://etidning.allehanda.se/#sign-in")
form_email = driver.find_element_by_name("prenlyLogin")
form_password = driver.find_element_by_name("prenlyPassword")
form_email.send_keys(args.email)
form_password.send_keys(args.password)
form_password.submit()
if args.verbose:
    print("Submitting credentials")

time.sleep(2)
latest_issue = driver.find_element_by_xpath("//a[contains(@href,'/369/Tidningen-Angermanland')]")
latest_issue.click()
print("Logged in")
if args.verbose:
    print("Opening latest issue")
# Todo: Add check for if issue corresponds with current date, otherwise sleep/die

time.sleep(2)
right_btn = driver.find_element_by_xpath("//button[@title='Nästa']")
left_btn = driver.find_element_by_xpath("//button[@title='Föregående']")

if args.verbose:
    print("Locating navigation buttons")

stored_requests = []
try:
    transverse_time = 1  # Sometimes not all blobs with pdf-requests load in time so we wait a bit.
    while True:
        time.sleep(transverse_time)

        # Page has 3 blobs loaded at a time
        current_img_blobs = driver.find_elements_by_xpath("//img[contains(@src, 'blob:')]")

        for blob in current_img_blobs:
            request = blob.get_attribute("data-src")
            if request not in stored_requests:  # Only add unique hashes
                if args.verbose:
                    print(f"Adding request {request}")
                stored_requests.append(request)
        if args.verbose:
            print("Advancing to next page")
        right_btn.click()  # Advance to next set of pages
except exceptions.ElementClickInterceptedException:
    print(f"Found {len(stored_requests)} pages")
    driver.quit()


temp_path = os.path.join(output_path, "tmp")
Path(temp_path).mkdir(parents=True, exist_ok=True)

current_date = date.today().strftime("%Y-%m-%d")
i = 1  # Indexer for individual pages, TODO: maybe make it prettier?
for request in stored_requests:
    if args.verbose:
        print(f"GET:ing response for {request}, writing file {current_date} - {i}.pdf to {temp_path}")
    response = requests.get(request, headers=headers)
    # Writing files to tempdir for merging
    with open(os.path.join(temp_path, f"{current_date} - {i}.pdf"), "wb") as file:
        file.write(response.content)
        i = i+1

# List only files and not dirs in temp_path
files_in_temp = [f for f in os.listdir(temp_path) if os.path.isfile(os.path.join(temp_path, f))]

errors_found = False
try:
    while True:  # We loop until we have removed all eventual error files.
        mergedPDF = PdfFileMerger()
        current_file = ""
        try:
            for file in files_in_temp:
                current_file = file
                mergedPDF.append(PdfFileReader(os.path.join(temp_path, file), "rb"))  # Merge files
            print(f"Writing output: Tidningen Allehanda - {current_date}.pdf")
            mergedPDF.write(os.path.join(output_path, f"Tidningen Allehanda - {current_date}.pdf"))  # Write output
            break
        except utils.PdfReadError:
            broken_path = os.path.join(output_path, "broken")
            print(f"File error found with {current_file}, we'll leave it alone, you can find it in {broken_path}")
            Path(broken_path).mkdir(parents=True, exist_ok=True)

            shutil.copy2(os.path.join(temp_path, current_file), os.path.join(broken_path, current_file))
            files_in_temp.remove(current_file)
            errors_found = True
except:  # TODO: Add some better exceptions...
    print("Oops, something went wrong, we'll still clean up after ourselves though")

if errors_found:
    print("Broken pdfs were found, maybe try https://pdf2go.com/repair-pdf) and merge them manually...")

if args.verbose:
    print("Cleaning up")
shutil.rmtree(temp_path)  # delete /tmp
if args.verbose:
    print("Bye, bye!")
