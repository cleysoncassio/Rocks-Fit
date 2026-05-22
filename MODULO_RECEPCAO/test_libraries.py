import sys

try:
    from selenium import webdriver
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    print("SELENIUM_AVAILABLE")
except ImportError:
    print("SELENIUM_NOT_AVAILABLE")

try:
    import playwright
    print("PLAYWRIGHT_AVAILABLE")
except ImportError:
    print("PLAYWRIGHT_NOT_AVAILABLE")
