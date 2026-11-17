import frappe
from frappe import _


def item_warehouse(item_code, company):
	return frappe.db.get_value(
		"Item Default", {"parent": item_code, "company": company}, "default_warehouse"
	)


@frappe.whitelist()
def get_item_warehouse(item_code: str, company: str):
	return item_warehouse(item_code, company)


def before_validate(doc, method=None):
	if not doc.is_new():
		return
	# Stage-wise production: a WO must consume the previous stage, never explode to RM
	if doc.use_multi_level_bom:
		doc.use_multi_level_bom = 0
		doc.set("required_items", [])  # validate rebuilds them single-level
		frappe.msgprint(_("Use Multi-Level BOM was turned off: each stage is a separate Work Order."), alert=True)

	# Target = production item's default warehouse (forced for Production Plan WOs)
	target = item_warehouse(doc.production_item, doc.company)
	if target and (doc.production_plan or not doc.fg_warehouse):
		doc.fg_warehouse = target


def validate(doc, method=None):
	"""Source = each component's default warehouse when BOM doesn't set one."""
	for row in doc.required_items:
		if not row.source_warehouse:
			row.source_warehouse = item_warehouse(row.item_code, doc.company)
