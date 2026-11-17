app_name = "prima_automotive"
app_title = "Prima Automotive"
app_publisher = "Prima Automotive"
app_description = "Customizations for Prima Automotive ERPNext implementation"
app_email = "prabhjotbal222@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "prima_automotive",
# 		"logo": "/assets/prima_automotive/logo.png",
# 		"title": "Prima Automotive",
# 		"route": "/prima_automotive",
# 		"has_permission": "prima_automotive.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `prima_automotive/dock/prima_automotive/prima_automotive.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prima_automotive/css/prima_automotive.css"
# app_include_js = "/assets/prima_automotive/js/prima_automotive.js"

# include js, css files in header of web template
# web_include_css = "/assets/prima_automotive/css/prima_automotive.css"
# web_include_js = "/assets/prima_automotive/js/prima_automotive.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prima_automotive/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prima_automotive/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "prima_automotive.utils.jinja_methods",
# 	"filters": "prima_automotive.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "prima_automotive.install.before_install"
# after_install = "prima_automotive.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "prima_automotive.uninstall.before_uninstall"
# after_uninstall = "prima_automotive.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prima_automotive.utils.before_app_install"
# after_app_install = "prima_automotive.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prima_automotive.utils.before_app_uninstall"
# after_app_uninstall = "prima_automotive.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "prima_automotive.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "prima_automotive.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prima_automotive.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["prima_automotive.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"prima_automotive.tasks.all"
# 	],
# 	"daily": [
# 		"prima_automotive.tasks.daily"
# 	],
# 	"hourly": [
# 		"prima_automotive.tasks.hourly"
# 	],
# 	"weekly": [
# 		"prima_automotive.tasks.weekly"
# 	],
# 	"monthly": [
# 		"prima_automotive.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "prima_automotive.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "prima_automotive.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "prima_automotive.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "prima_automotive.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prima_automotive.utils.before_request"]
# after_request = ["prima_automotive.utils.after_request"]

# Job Events
# ----------
# before_job = ["prima_automotive.utils.before_job"]
# after_job = ["prima_automotive.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"prima_automotive.auth.validate"
# ]

# on_social_login = "prima_automotive.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Prima Automotive customizations
doctype_js = {"Work Order": "public/js/work_order.js"}
after_migrate = "prima_automotive.install.after_migrate"

doc_events = {
	"Stock Entry": {
		"validate": "prima_automotive.overrides.stock_entry.validate",
		"before_submit": "prima_automotive.overrides.stock_entry.before_submit",
		"on_submit": "prima_automotive.overrides.stock_entry.on_submit",
		"on_cancel": "prima_automotive.overrides.stock_entry.on_cancel",
	},
	"Work Order": {
		"before_validate": "prima_automotive.overrides.work_order.before_validate",
		"validate": "prima_automotive.overrides.work_order.validate",
	},
	"Purchase Receipt": {
		"on_submit": "prima_automotive.overrides.purchase_receipt.on_submit",
	},
}
