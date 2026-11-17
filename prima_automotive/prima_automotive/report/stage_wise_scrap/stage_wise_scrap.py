import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Stock Entry"), "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
		{"label": _("Work Order"), "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
		{"label": _("Produced Item"), "fieldname": "production_item", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Link", "options": "Item Group", "width": 110},
		{"label": _("Produced Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Scrap Item"), "fieldname": "scrap_item", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Standard Scrap"), "fieldname": "standard_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Actual Scrap"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Float", "width": 100},
		{"label": _("Variance %"), "fieldname": "variance_pct", "fieldtype": "Percent", "width": 100},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 70},
	]


def get_data(filters):
	conditions = ""
	if filters.from_date:
		conditions += " and se.posting_date >= %(from_date)s"
	if filters.to_date:
		conditions += " and se.posting_date <= %(to_date)s"
	if filters.stage:
		conditions += " and fg_item.item_group = %(stage)s"
	if filters.production_item:
		conditions += " and fg.item_code = %(production_item)s"

	rows = frappe.db.sql(
		f"""
		select se.posting_date, se.name as stock_entry, se.work_order,
			fg.item_code as production_item, fg_item.item_group as stage, fg.transfer_qty as produced_qty,
			sc.item_code as scrap_item, sc.standard_scrap_qty as standard_qty,
			sc.transfer_qty as actual_qty, sc.stock_uom as uom
		from `tabStock Entry` se
		join `tabStock Entry Detail` fg on fg.parent = se.name and fg.is_finished_item = 1
		join `tabItem` fg_item on fg_item.name = fg.item_code
		join `tabStock Entry Detail` sc on sc.parent = se.name and sc.secondary_item_type = 'Scrap'
		where se.docstatus = 1 and se.purpose = 'Manufacture' {conditions}
		order by se.posting_date desc, se.name""",
		filters,
		as_dict=True,
	)
	for r in rows:
		r.variance = flt(r.actual_qty) - flt(r.standard_qty)
		r.variance_pct = (r.variance / r.standard_qty * 100) if r.standard_qty else None
	return rows
