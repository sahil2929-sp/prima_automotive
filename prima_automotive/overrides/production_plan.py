import frappe

from prima_automotive.overrides.work_order import item_warehouse


def wip_warehouse(company):
	return frappe.get_cached_value("Company", company, "default_wip_warehouse")


@frappe.whitelist()
def get_wip_warehouse(company: str):
	return wip_warehouse(company)


def before_validate(doc, method=None):
	"""Draft plan: SFG stock checked in WIP, sub-assembly rows fetched without the button."""
	if doc.docstatus:
		return
	if not doc.sub_assembly_warehouse:
		doc.sub_assembly_warehouse = wip_warehouse(doc.company)
	ready = doc.po_items and all(r.item_code and r.bom_no and r.planned_qty for r in doc.po_items)
	if ready and not doc.sub_assembly_items:
		doc.get_sub_assembly_items()


def validate(doc, method=None):
	"""Each row's target warehouse = that item's default warehouse."""
	for table, field in (("po_items", "warehouse"), ("sub_assembly_items", "fg_warehouse")):
		for row in doc.get(table):
			wh = item_warehouse(row.get("item_code") or row.get("production_item"), doc.company)
			if wh:
				row.set(field, wh)
