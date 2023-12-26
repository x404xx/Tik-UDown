import logging
import os
import time

import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from exception import AccountNotFoundError, InvalidUrlError
from terminal.console import console
from terminal.logo import ProgramLogo

from .captchasolver import CaptchaSolver


class TiktokScraper(CaptchaSolver, ProgramLogo):
    def __init__(
        self, channel_url: str, headless: bool, enable_log: bool, max_windows: bool
    ):
        self.enable_log = enable_log
        self.headless = headless
        self.max_windows = max_windows
        self.channel_url = self._sanitize_url(channel_url)
        self.driver = self._setup_driver()
        self.scroll_distance = 5000
        self.scroll_delay = 5

        if self.enable_log:
            self._setup_logging()

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--no-sandbox")
        if self.headless:
            chrome_options.add_argument("--headless")
        driver = uc.Chrome(options=chrome_options)
        if self.max_windows:
            driver.maximize_window()
        driver.set_window_size(930, 800)
        driver.implicitly_wait(3)
        return driver

    def _setup_logging(self):
        log_name = "tiktok.log"
        log_directory = "Tiktok LOG"
        os.makedirs(log_directory, exist_ok=True)
        filename = os.path.join(log_directory, log_name)

        logging.basicConfig(
            level="NOTSET",
            format="%(asctime)s - %(levelname)s - (%(message)s)",
            datefmt="[%d|%m|%Y - %I:%M:%S %p]",
            filename=filename,
            filemode="w",
        )

    def _get_source(self):
        self.setup_logo()
        with console.status(
            f"[cyan]Opening homepage[/] - {self.channel_url}",
            spinner="point",
            spinner_style="magenta",
        ):
            self.driver.get(self.channel_url)

    def _account_not_exists_or_private(self):
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, ".css-1ovqurc-PTitle")
            element_text = element.text
            if (
                "Couldn't find this account"
                or "This account is private" in element_text
            ):
                self.driver.quit()
                raise AccountNotFoundError(f"{element_text} '{self.channel_url}'")
        except NoSuchElementException:
            pass

    def _is_captcha(self, captcha_verify: str):
        try:
            self.driver.find_element(By.ID, captcha_verify)
            console.print(
                ":lock_with_ink_pen: [red]Found Captcha. [yellow1]Trying to solve.."
            )
            return True
        except NoSuchElementException:
            console.print(
                ":unlocked: [green]Captcha not found. [yellow1]Trying to grab links..[/]"
            )
            return False

    def _scroll_page(self):
        with console.status(
            "[cyan]Scrolling page to the bottom..[/]",
            spinner="point",
            spinner_style="magenta",
        ) as status:
            while True:
                prev_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )
                self.driver.execute_script(
                    f"window.scrollBy(0, {self.scroll_distance});"
                )
                time.sleep(self.scroll_delay)
                current_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )
                if current_height == prev_height:
                    status.stop()
                    console.print(
                        ":checkered_flag: [pale_green1]Please wait! Saving video links to the text file..[/]"
                    )
                    break
                self.scroll_distance += 5000

    def _extract_link(self):
        containers = self.driver.find_elements(
            By.CSS_SELECTOR, '[class*="-DivItemContainerV2"]'
        )
        video_links = list(
            container.find_element(
                By.CSS_SELECTOR, '[data-e2e="user-post-item"] a'
            ).get_attribute("href")
            for container in containers
        )
        return video_links

    def _sanitize_url(self, tiktok_channel: str):
        base_url = "https://www.tiktok.com/@"

        if tiktok_channel.startswith(base_url):
            return tiktok_channel
        elif tiktok_channel.startswith("@"):
            return base_url + tiktok_channel[1:]
        elif tiktok_channel.isalnum():
            return base_url + tiktok_channel
        else:
            raise InvalidUrlError(f"'{tiktok_channel}' is not a valid input!")

    def _process_links(self, video_links: list):
        data = "\n".join(video_links)

        url_directory = "Tiktok URL"
        username = f"{self.get_username}.txt"
        os.makedirs(url_directory, exist_ok=True)
        filename = os.path.join(url_directory, username)

        with open(filename, "w", encoding="utf-8") as file:
            file.write(data)

        console.print(
            f'\n{len(video_links)} links has been saved in "[blue1]{filename}[/]"\n'
        )
        time.sleep(1)
        self.driver.quit()

    def _save_links(self):
        self._scroll_page()
        video_links = self._extract_link()
        self._process_links(video_links)

    def _captcha_img_src(self, captcha_verify: str):
        captcha_img = self.driver.find_element(By.ID, captcha_verify)
        if captcha_img.get_attribute("src"):
            time.sleep(1)
            captcha_img.screenshot("puzzle.png")

    @property
    def get_username(self):
        return self.channel_url.split("@")[-1]

    def scrape_video_link(self):
        self._get_source()
        self._account_not_exists_or_private()
        captcha_verify = "captcha-verify-image"
        if self._is_captcha(captcha_verify):
            while True:
                self._captcha_img_src(captcha_verify)
                if self.solve_puzzle(self.driver):
                    self._save_links()
                    break

                time.sleep(2)
                continue
        else:
            time.sleep(1)
            self._save_links()
