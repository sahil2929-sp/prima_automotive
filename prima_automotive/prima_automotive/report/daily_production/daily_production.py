"""Daily production entries: who made how many pieces, on which machine, against which Work Order."""

import frappe
from frappe import _
from frappe.utils import flt

from prima_automotive.overrides.stock_entry import row_batches

STAGES = {"CT": "Cutting", "BR": "Boring", "ST": "Stamping", "CH": "Chamfering"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
		{"label": _("Work Order"), "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 95},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 190},
		{"label": _("Operator"), "fieldname": "operator", "fieldtype": "Link", "options": "Employee", "width": 115},
		{"label": _("Operator Name"), "fieldname": "operator_name", "fieldtype": "Data", "width": 130},
		{"label": _("Machine"), "fieldname": "machine", "fieldtype": "Link", "options": "Workstation", "width": 110},
		{"label": _("Pieces Made"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 105, "precision": 0},
		{"label": _("WO Qty"), "fieldname": "wo_qty", "fieldtype": "Float", "width": 85, "precision": 0},
		{"label": _("Made So Far"), "fieldname": "cumulative_qty", "fieldtype": "Float", "width": 105, "precision": 0},
		{"label": _("Balance"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 85, "precision": 0},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 140},
		{"label": _("Scrap (Kg)"), "fieldname": "scrap_qty", "fieldtype": "Float", "width": 90},
		{"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
		{"label": _("Stock Entry"), "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
	]


def get_data(filters):
	se, fg, wo = frappe.qb.DocType("Stock Entry"), frappe.qb.DocType("Stock Entry Detail"), frappe.qb.DocType("Work Order")
	query = (
		frappe.qb.from_(se)
		.join(fg).on((fg.parent == se.name) & (fg.is_finished_item == 1))
		.join(wo).on(wo.name == se.work_order)
		.select(
			se.name.as_("stock_entry"), se.posting_date, se.posting_time, se.work_order, se.machine, se.operator, se.operator_name,
			fg.name.as_("row_name"), fg.item_code, fg.item_name, fg.transfer_qty.as_("produced_qty"), fg.batch_no,
			fg.serial_and_batch_bundle, wo.qty.as_("wo_qty"), wo.sales_order, wo.production_plan,
		)
		.where((se.docstatus == 1) & (se.purpose == "Manufacture"))
		.orderby(se.work_order).orderby(se.posting_date).orderby(se.posting_time).orderby(se.creation)
	)
	if filters.company:
		query = query.where(se.company == filters.company)
	for field, column in (("work_order", se.work_order), ("item_code", fg.item_code), ("sales_order", wo.sales_order),
			("production_plan", wo.production_plan)):
		if filters.get(field):
			query = query.where(column == filters.get(field))
	if filters.stage:
		prefix = next((p for p, s in STAGES.items() if s == filters.stage), None)
		if prefix:
			query = query.where(fg.item_code.like(f"{prefix}-%"))

	rows = query.run(as_dict=True)
	scrap = scrap_by_entry([r.stock_entry for r in rows])
	made, data = {}, []
	for r in rows:
		# running total covers every entry of the Work Order, even ones outside the date range
		made[r.work_order] = made.get(r.work_order, 0) + flt(r.produced_qty)
		if filters.from_date and str(r.posting_date) < str(filters.from_date):
			continue
		if filters.to_date and str(r.posting_date) > str(filters.to_date):
			continue
		if any(filters.get(f) and filters.get(f) != r.get(f) for f in ("operator", "machine")):
			continue
		r.stage = STAGES.get(r.item_code.split("-")[0], "")
		r.cumulative_qty = made[r.work_order]
		r.balance_qty = max(flt(r.wo_qty) - r.cumulative_qty, 0)
		r.batch_no = r.batch_no or next(iter(b for b, _q in row_batches(frappe._dict(
			doctype="Stock Entry Detail", name=r.row_name, serial_and_batch_bundle=r.serial_and_batch_bundle))), None)
		r.scrap_qty = scrap.get(r.stock_entry, 0)
		data.append(r)
	return data


def scrap_by_entry(entries):
	if not entries:
		return {}
	from frappe.query_builder.functions import Sum

	d = frappe.qb.DocType("Stock Entry Detail")
	return dict(
		frappe.qb.from_(d).select(d.parent, Sum(d.transfer_qty))
		.where(d.parent.isin(entries) & (d.secondary_item_type == "Scrap"))
		.groupby(d.parent).run()
	)


def get_summary(data):
	if not data:
		return []
	return [
		{"label": _("Pieces Made"), "value": sum(flt(r.produced_qty) for r in data), "datatype": "Float", "indicator": "Blue"},
		{"label": _("Entries"), "value": len(data), "datatype": "Int"},
		{"label": _("Work Orders"), "value": len({r.work_order for r in data}), "datatype": "Int"},
		{"label": _("Operators"), "value": len({r.operator for r in data if r.operator}), "datatype": "Int"},
		{"label": _("Scrap (Kg)"), "value": sum(flt(r.scrap_qty) for r in data), "datatype": "Float", "indicator": "Red"},
	]


def get_chart(data):
	by_operator = {}
	for r in data:
		key = r.operator_name or r.operator or _("Not set")
		by_operator[key] = by_operator.get(key, 0) + flt(r.produced_qty)
	if not by_operator:
		return None
	return {
		"data": {"labels": list(by_operator), "datasets": [{"name": _("Pieces Made"), "values": list(by_operator.values())}]},
		"type": "bar",
		"title": _("Pieces Made by Operator"),
	}
