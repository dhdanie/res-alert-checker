import json
import random
import time
import sys
import logging
from dataclasses import dataclass

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from seleniumwire.utils import decode as sw_decode
from selenium.webdriver.firefox.options import Options
from gmail_scraper import MailAuth
from types import SimpleNamespace


class Email:
    def __init__(self, search_id, available_times):
        self.search_id = search_id
        self.available_times = available_times


log = logging.getLogger(__name__)
logging.getLogger("seleniumwire").setLevel(100)
logging.getLogger("selenium").setLevel(100)
logging.getLogger("hpack").setLevel(100)
logging.getLogger("urllib3").setLevel(100)
logging.getLogger("googleapiclient").setLevel(100)
logging.getLogger("google").setLevel(100)
log.setLevel(logging.INFO)
logging.basicConfig(level=logging.DEBUG)


class AuthGrabber:  # ARG USAGE: identical to init order
    def __init__(
        self,
        login_id: int,
        party: int,
        date: str,
        res_time: str,
        res_name: str,
        res_id: str,
    ):
        self.party = party
        self.date = date
        self.res_time = res_time
        self.res_name = res_name
        self.login_id = login_id
        self.res_id = res_id

        self.options = Options()
        self.options.add_argument("-headless")
        self.profile = webdriver.FirefoxProfile()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.profile.set_preference("general.useragent.override", self.user_agent)
        self.options.profile = self.profile
        self.driver = webdriver.Firefox(options=self.options)
        # driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, timeout=60, poll_frequency=0.5)
        self.swait = WebDriverWait(self.driver, timeout=15, poll_frequency=0.5)

    def reset_driver(self):
        log.debug("start of reset_driver")
        self.driver.close()
        self.driver = webdriver.Firefox(options=self.options)
        self.wait = WebDriverWait(self.driver, timeout=60, poll_frequency=0.5)
        self.swait = WebDriverWait(self.driver, timeout=15, poll_frequency=0.5)
        log.debug("end of reset_driver")

    def close(self):
        log.debug("closing driver")
        self.driver.close()

    def check_exists(self, by, value):
        try:
            self.driver.find_element(by=by, value=value)
        except NoSuchElementException:
            return False
        return True

    def rwait(self):
        time.sleep(1 + random.random())
        self.driver.execute_script(f"window.scrollTo(0, {random.random() * 10})")

    def login(self):
        # Load disney page
        log.debug("loading https://disneyworld.disney.go.com/dine-res/availability")
        self.driver.get("https://disneyworld.disney.go.com/dine-res/availability")
        handle = self.driver.current_window_handle

        # Navigate to alternate login screen
        log.debug("navigate to email login")
        self.wait.until(EC.visibility_of_element_located((By.ID, "oneid-iframe")))
        self.driver.switch_to.frame(
            self.driver.find_element(by=By.ID, value="oneid-iframe")
        )
        self.driver.find_element(
            by=By.LINK_TEXT, value="Looking for username login?"
        ).click()
        self.rwait()
        self.driver.find_element(by=By.ID, value="HelpSigningIn").click()
        self.rwait()

        # Finish login process and switch focus back to window

        log.debug("inputting login information: ")
        log.debug(f"    - username: resfinderdisney+{self.login_id}@gmail.com")
        self.wait.until(EC.visibility_of_element_located((By.ID, "OtpInputLoginValue")))
        self.driver.find_element(by=By.ID, value="OtpInputLoginValue").send_keys(
            f"resfinderdisney+{self.login_id}@gmail.com"
        )
        self.rwait()
        self.driver.find_element(by=By.ID, value="BtnSubmit").click()
        self.rwait()

        log.debug("getting email code")
        self.driver.find_element(by=By.ID, value="otp-code-input-0").send_keys(
            MailAuth().read_emails(self.login_id)
        )
        self.rwait()
        self.driver.find_element(by=By.ID, value="BtnSubmit").click()
        self.rwait()
        self.wait.until(EC.visibility_of_element_located((By.ID, "BtnDone"))).click()
        self.rwait()
        self.driver.switch_to.window(handle)
        log.debug("end of login")

    def perform_search(self):
        log.debug("performing search:")
        log.debug(f"    - party size: {self.party}")
        log.debug(f"    - date: {self.date}")
        log.debug(f"    - time: {self.res_time}")

        # Select party size
        log.debug("waiting for initial page load")  # TODO: Add movmement to fix page
        self.wait.until(EC.visibility_of_element_located((By.ID, f"count-selector1")))

        # Wait and check again to ensure page reload doesn't happen after location found breaking later sections
        time.sleep(3)
        log.debug("looking for count-selector1")
        self.wait.until(EC.visibility_of_element_located((By.ID, f"count-selector1")))
        log.debug("count-selector1 found")

        log.debug("looking for sec-container")
        self.wait.until(EC.visibility_of_element_located((By.ID, "sec-container")))
        log.debug("sec-container found")
        log.debug("waiting for invisibility of sec-container")
        self.wait.until(EC.invisibility_of_element((By.ID, "sec-container")))

        log.debug("selecting party size")
        if self.party > 10:
            log.debug("  - party size is greater than 10, go to next page")
            self.swait.until(
                EC.element_to_be_clickable(
                    self.driver.find_element(by=By.CLASS_NAME, value="di-next-2")
                )
            ).click()
            self.rwait()
        self.swait.until(
            EC.element_to_be_clickable(
                self.driver.find_element(by=By.ID, value=f"count-selector{self.party}")
            )
        ).click()
        self.rwait()

        # Select date
        log.debug("selecting reservation date")
        self.wait.until(
            EC.visibility_of_element_located((By.CLASS_NAME, "calendar-cell"))
        )
        if not self.check_exists(By.CSS_SELECTOR, f"[data-date='{self.date}'"):
            log.debug("switching datepicker page")
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "[aria-label='Next Month']")
                )
            ).click()
            self.rwait()
        self.swait.until(
            EC.element_to_be_clickable(
                self.driver.find_element(
                    by=By.CSS_SELECTOR, value=f"[data-date='{self.date}'"
                )
            )
        ).click()
        self.rwait()

        # Select time
        log.debug("select reservation time")
        self.swait.until(
            EC.element_to_be_clickable(
                self.driver.find_element(by=By.ID, value="unique_id_time_All Day")
            )
        ).click()
        self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "offers")))

    def format_output(self):  # TODO: fix this, cutting off offers
        # Locate relevant http request
        log.debug("begin of format_output")
        data = "not found"
        log.debug("find http request containing search data")
        for request in self.driver.requests:
            if (
                request.url
                == f"https://disneyworld.disney.go.com/dine-res/api/availability/{self.party}/{self.date}/00:00:00,23:59:59"
            ):
                data = sw_decode(
                    request.response.body,
                    request.response.headers.get("Content-Encoding", "identity"),
                )
                data = data.decode("utf8")

        log.debug("format raw data")

        log.debug("casting json")
        result = json.loads(data)
        result = result["restaurant"][self.res_id]["offers"][self.date]
        offers = []
        log.debug("checking for availability in specified timeframe")
        for period in result:
            if self.res_time.lower().__contains__(period["mealPeriodType"].lower()):
                offers = period["offersByAccessibility"][0]

        if offers:
            offer_times = []
            for offer_time in offers["offers"]:
                offer_times.append(offer_time["label"])
            log.debug(offer_times)
            return offer_times
        return []

    def get_search(self):  # TODO: Send email if reservation found
        log.debug(
            f"Search info -> party size:{self.party}, date:{self.date}, time:{self.res_time}, restaurant:{self.res_name}"
        )

        try:
            self.login()
            self.perform_search()
            return self.format_output()
        except ValueError as v:
            log.debug(f"ValueError Found (likely no available times) - {v}")
        except Exception as e:
            log.critical(f"Exception encountered - \n{e}")
            return []


# login_id<int>, party<int>, date<string>(YYYY-MM-DD), res_time<string>(BREAKFAST|BRUNCH|LUNCH|DINNER), res_name<string>(restaurant name), res_id<string>
auth = AuthGrabber(
    int(sys.argv[1]),
    int(sys.argv[2]),
    sys.argv[3],
    sys.argv[4],
    sys.argv[5],
    sys.argv[6],
)

try:
    print(len(auth.get_search()) > 0)
finally:
    auth.close()
