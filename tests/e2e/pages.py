from datetime import date
from playwright.sync_api import Locator, Page

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    @property
    def flash_success(self) -> Locator:
        return self.page.get_by_test_id("flash-success")

    @property
    def flash_error(self) -> Locator:
        return self.page.get_by_test_id("flash-error")

    def logout(self) -> None:
        self.page.get_by_test_id("logout").click()


class LoginPage(BasePage):
    def open(self) -> "LoginPage":
        self.page.goto("/login")
        return self

    def login(self, email: str, password: str) -> None:
        self.page.get_by_test_id("login-email").fill(email)
        self.page.get_by_test_id("login-password").fill(password)
        self.page.get_by_test_id("login-submit").click()

    @property
    def error(self) -> Locator:
        return self.flash_error


class DashboardPage(BasePage):
    @property
    def greeting(self) -> Locator:
        return self.page.get_by_test_id("greeting")

    @property
    def request_rows(self) -> Locator:
        return self.page.get_by_test_id("request-row")

    def remaining(self, leave_type: str) -> Locator:
        row = self.page.get_by_test_id(f"balance-row-{leave_type.lower()}")
        return row.get_by_test_id("remaining")

    def apply(self, leave_type: str, start: date, end: date, reason: str = "") -> None:
        self.page.get_by_test_id("leave-type").select_option(label=leave_type)
        self.page.get_by_test_id("start-date").fill(start.isoformat())
        self.page.get_by_test_id("end-date").fill(end.isoformat())
        self.page.get_by_test_id("reason").fill(reason)
        self.page.get_by_test_id("apply-submit").click()


class ApprovalsPage(BasePage):
    def open(self) -> "ApprovalsPage":
        self.page.goto("/approvals")
        return self

    @property
    def no_pending(self) -> Locator:
        return self.page.get_by_test_id("no-pending")

    def row_for(self, employee_name: str) -> Locator:
        return self.page.get_by_test_id("approval-row").filter(has_text=employee_name)

    def approve(self, employee_name: str, comment: str = "") -> None:
        row = self.row_for(employee_name)
        row.get_by_test_id("decision-comment").fill(comment)
        row.get_by_test_id("approve-button").click()

    def reject(self, employee_name: str, comment: str = "") -> None:
        row = self.row_for(employee_name)
        row.get_by_test_id("decision-comment").fill(comment)
        row.get_by_test_id("reject-button").click()