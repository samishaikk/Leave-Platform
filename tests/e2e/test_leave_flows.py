import re
from datetime import date, timedelta
import pytest
from playwright.sync_api import expect

from tests.e2e.helpers import login_as, next_weekday
from tests.e2e.pages import ApprovalsPage, DashboardPage, LoginPage
from tests.factories import make_leave_request

pytestmark = pytest.mark.e2e


def test_wrong_password_shows_an_error(page, seeded):
    login = LoginPage(page).open()
    login.login(seeded.ravi.email, "wrong-password")
    expect(login.error).to_contain_text("Incorrect email or password")
    expect(page).to_have_url(re.compile(r"/login$"))


def test_logged_out_visitor_is_sent_to_login(page, seeded):
    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))


def test_employee_sees_dashboard_without_approvals_link(page, seeded):
    login_as(page, seeded.ravi)
    dashboard = DashboardPage(page)
    expect(dashboard.greeting).to_have_text("Hello, Ravi")
    expect(dashboard.remaining("Annual")).to_have_text("18")
    expect(page.get_by_test_id("nav-approvals")).to_have_count(0)


def test_employee_applies_for_leave(page, seeded):
    login_as(page, seeded.ravi)
    dashboard = DashboardPage(page)
    day = next_weekday(10)

    dashboard.apply("Annual", day, day, "family event")

    expect(dashboard.flash_success).to_contain_text("submitted")
    expect(dashboard.request_rows).to_have_count(1)
    status = dashboard.request_rows.first.get_by_test_id("request-status")
    expect(status).to_have_text("pending")
    
    if day.year == date.today().year:
        expect(dashboard.remaining("Annual")).to_have_text("17")


def test_short_notice_is_refused_with_a_message(page, seeded):
    login_as(page, seeded.ravi)
    dashboard = DashboardPage(page)
    tomorrow = date.today() + timedelta(days=1)

    dashboard.apply("Annual", tomorrow, tomorrow)

    expect(dashboard.flash_error).to_contain_text("cannot start before")
    expect(page.get_by_test_id("no-requests")).to_be_visible()


def test_overlapping_request_is_refused(page, seeded):
    login_as(page, seeded.ravi)
    dashboard = DashboardPage(page)
    day = next_weekday(10)

    dashboard.apply("Annual", day, day)
    expect(dashboard.flash_success).to_be_visible()

    dashboard.apply("Annual", day, day)
    expect(dashboard.flash_error).to_contain_text("already have a leave request")
    expect(dashboard.request_rows).to_have_count(1)


def test_full_approval_workflow_across_two_users(page, seeded):
    day = next_weekday(10)

    # Ravi applies
    login_as(page, seeded.ravi)
    dashboard = DashboardPage(page)
    dashboard.apply("Annual", day, day, "family event")
    expect(dashboard.flash_success).to_be_visible()
    dashboard.logout()

    # Meera approves
    login_as(page, seeded.manager)
    approvals = ApprovalsPage(page).open()
    approvals.approve("Ravi")
    expect(approvals.flash_success).to_contain_text("approved")
    expect(approvals.no_pending).to_be_visible()
    approvals.logout()

    # Ravi sees the decision
    login_as(page, seeded.ravi)
    status = dashboard.request_rows.first.get_by_test_id("request-status")
    expect(status).to_have_text("approved")


def test_rejection_needs_a_comment(page, seeded):
    day = next_weekday(10)
    make_leave_request(seeded.db, seeded.ravi, seeded.types["Annual"], day, day, 1)

    login_as(page, seeded.manager)
    approvals = ApprovalsPage(page).open()
    approvals.reject("Ravi")  
    expect(approvals.flash_error).to_contain_text("comment is required")
    expect(approvals.row_for("Ravi")).to_be_visible()

    approvals.reject("Ravi", "team is short that week")
    expect(approvals.flash_success).to_contain_text("rejected")
    expect(approvals.no_pending).to_be_visible()


def test_employee_cannot_open_approvals(page, seeded):
    login_as(page, seeded.ravi)
    page.goto("/approvals")
    expect(DashboardPage(page).flash_error).to_contain_text("Manager access only")