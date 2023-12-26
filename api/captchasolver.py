import os
import time
from collections import Counter
from typing import Any

import cv2 as cv
import numpy as np
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from terminal.console import console


class CaptchaSolver:
    @staticmethod
    def _load_image():
        """Load the image and convert it to grayscale."""
        img = cv.imread("puzzle.png")
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        os.remove("puzzle.png")
        return gray

    @staticmethod
    def _get_corners(gray: np.ndarray):
        """Detect corners in the image."""
        corners = cv.goodFeaturesToTrack(gray, 15, 0.05, 1)
        return np.intp(corners)

    @staticmethod
    def _get_x_offset(corners: np.ndarray):
        """Calculate the x offset for the slider."""
        x_array = [i.ravel()[0] for i in corners if i.ravel()[0] > 70]
        x_array.sort()
        unic = Counter(x_array)
        return next((x - 8 for x in x_array if unic[x] > 1), None)

    @staticmethod
    def _perform_slide(driver: WebDriver, x_offset: Any):
        """Perform the slide action."""
        slider = driver.find_element(By.CLASS_NAME, "secsdk-captcha-drag-icon")
        y_offset = 0
        action_c = ActionChains(driver)
        steps_count = 5
        step = x_offset / steps_count
        action = action_c.click_and_hold(slider)
        for _ in range(0, steps_count):
            action.move_by_offset(step, y_offset)
        action.release().perform()
        time.sleep(1)

    @staticmethod
    def _check_verification(driver: WebDriver):
        """Check if the captcha was solved successfully."""
        message = (
            driver.find_element(By.CLASS_NAME, "msg")
            .find_element(By.TAG_NAME, "div")
            .text
        )
        success = "Verification complete" in message or "complete" in message
        console.print(
            f":heavy_check_mark:  [green1]Captcha solved.[/]"
            if success
            else ":no_entry: [red1]Captcha solve failed. [cyan1]Now retrying..[/]"
        )
        return success

    @classmethod
    def solve_puzzle(cls, driver: WebDriver):
        """Main function to solve the captcha puzzle."""
        gray = cls._load_image()
        corners = cls._get_corners(gray)
        x_offset = cls._get_x_offset(corners)
        cls._perform_slide(driver, x_offset)
        return cls._check_verification(driver)
