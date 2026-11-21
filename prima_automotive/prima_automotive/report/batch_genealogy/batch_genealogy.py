import frappe
from frappe import _

MAX_DEPTH = 10


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.batch:
		return get_columns(), []
	backward = (filters.direction or "Backward") == "Backward"
	data = [batch_row(filters.batch, None, 0)]
	walk(filters.batch, backward, 1, data, {filters.batch})
	return get_columns(), data


def get_columns():
	return [
		{"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 200},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 110},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Stock Entry"), "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
		{"label": _("Work Order"), "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
		{"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
		{"label": _("Trace Lot"), "fieldname": "trace_lot", "fieldtype": "Data", "width": 180},
	]


def batch_row(batch, link, indent):
	b = frappe.db.get_value("Batch", batch, ["item", "item_name", "supplier", "trace_lot", "work_order", "sales_order"], as_dict=True) or {}
	return {
		"batch": batch, "indent": indent, "item": b.get("item"), "item_name": b.get("item_name"),
		"stage": b.get("item") and frappe.db.get_value("Item", b.item, "item_group"),
		"qty": link.qty if link else None, "stock_entry": link.stock_entry if link else None,
		"work_order": b.get("work_order"), "sales_order": b.get("sales_order"),
		"supplier": b.get("supplier"), "trace_lot": b.get("trace_lot"),
	}


def walk(batch, backward, indent, data, seen):
	if indent > MAX_DEPTH:
		return
	if backward:  # what went into this batch
		links = frappe.get_all("Batch Source", {"parent": batch, "parenttype": "Batch"},
			["source_batch as batch", "qty", "stock_entry"])
	else:  # where this batch was used
		links = frappe.get_all("Batch Source", {"source_batch": batch, "parenttype": "Batch"},
			["parent as batch", "qty", "stock_entry"])
	for link in links:
		data.append(batch_row(link.batch, link, indent))
		if link.batch not in seen:
			seen.add(link.batch)
			walk(link.batch, backward, indent + 1, data, seen)
