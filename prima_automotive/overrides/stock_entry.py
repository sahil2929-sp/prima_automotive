import frappe
from frappe import _
from frappe.utils import flt


def validate(doc, method=None):
	if doc.purpose == "Manufacture":
		check_machine_operator(doc)
		set_standard_scrap_qty(doc)
		set_output_batch(doc)


def check_machine_operator(doc):
	"""Each daily production entry records who ran it and on which machine."""
	missing = [_(label) for field, label in (("machine", "Machine"), ("operator", "Operator"))
		if not (doc.get(field) or "").strip()]
	if missing:
		frappe.throw(_("Please enter {0} for this production entry.").format(" and ".join(missing)),
			title=_("Missing Details"))


def set_output_batch(doc):
	"""Output batch keeps the input batch's number with this stage's prefix
	(RM/26-27/00006 -> CT/26-27/00006 -> BR/26-27/00006), never a -2 suffix.
	All daily entries of one Work Order share that batch."""
	for row in doc.items:
		if not row.is_finished_item or row.batch_no or row.serial_and_batch_bundle:
			continue
		if not frappe.db.get_value("Item", row.item_code, "has_batch_no"):
			continue
		row.batch_no = (
			work_order_batch(row.item_code, doc.work_order)
			or input_numbered_batch(row.item_code, doc)
			or new_batch(row.item_code, doc)
		)
		row.use_serial_batch_fields = 1


def work_order_batch(item_code, work_order):
	"""Batch already made for this item by an earlier (or draft) entry of the same Work Order."""
	return work_order and frappe.db.get_value(
		"Batch", {"item": item_code, "work_order": work_order}, "name", order_by="creation asc"
	)


def input_numbered_batch(item_code, doc):
	"""STAGE/FY/<running no of the main input batch>; reused if this item already has it."""
	main_input = main_input_batch(doc)
	prefix = (frappe.db.get_value("Item", item_code, "batch_number_series") or "").split("/")[0].strip(".")
	parts = (main_input or "").split("/")
	if not prefix or len(parts) < 3:
		return None  # no input batch in PREFIX/FY/NO format
	name = "/".join([prefix, *parts[1:]])
	owner = frappe.db.get_value("Batch", name, "item")
	if owner and owner != item_code:
		return None  # number taken by another item: fall back to the series
	if not owner:
		new_batch(item_code, doc, name)
	elif doc.work_order and not frappe.db.get_value("Batch", name, "work_order"):
		frappe.db.set_value("Batch", name, "work_order", doc.work_order)
	return name


def main_input_batch(doc):
	"""Input batch with the largest qty: the row's batch, else this Work Order's transfers,
	else the batch FIFO will pick at submit."""
	rows = [d for d in doc.items if d.s_warehouse and not d.is_finished_item and not d.secondary_item_type]
	inputs = [(b, abs(flt(q))) for d in rows for b, q in row_batches(d) if b]
	if not inputs and doc.work_order:
		items = {d.item_code for d in rows}
		for se in frappe.get_all("Stock Entry", {"work_order": doc.work_order, "docstatus": 1,
				"purpose": "Material Transfer for Manufacture"}, pluck="name"):
			for d in frappe.get_doc("Stock Entry", se).items:
				if d.item_code in items:
					inputs += [(b, abs(flt(q))) for b, q in row_batches(d) if b]
	if not inputs:
		inputs = [(b, q) for d in rows for b, q in fifo_batches(d)]
	return inputs and max(inputs, key=lambda x: x[1])[0]


def fifo_batches(row):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_batch_nos

	if not frappe.db.get_value("Item", row.item_code, "has_batch_no"):
		return []
	picked = get_auto_batch_nos(frappe._dict(item_code=row.item_code, warehouse=row.s_warehouse,
		qty=row.transfer_qty or row.qty, based_on="FIFO"))
	return [(b.batch_no, flt(b.qty)) for b in picked or [] if b.get("batch_no")]


def new_batch(item_code, doc, name=None):
	# Work Order set now so a second draft of the same order finds this batch
	batch = frappe.get_doc({"doctype": "Batch", "item": item_code, "batch_id": name, "work_order": doc.work_order,
		"manufacturing_date": doc.posting_date})
	batch.flags.ignore_links = True
	return batch.insert(ignore_permissions=True).name


def on_submit(doc, method=None):
	if doc.purpose == "Manufacture":
		link_batches(doc)
		set_batch_orders(doc)


def on_cancel(doc, method=None):
	frappe.db.delete("Batch Source", {"parenttype": "Batch", "stock_entry": doc.name})
	for batch in output_batches(doc):
		refresh_trace_lot(batch)


def scrap_rows(doc):
	return [d for d in doc.items if d.secondary_item_type == "Scrap"]


def set_standard_scrap_qty(doc):
	"""Standard scrap = BOM scrap qty scaled to produced qty."""
	fg_qty = sum(flt(d.transfer_qty) for d in doc.items if d.is_finished_item)
	for d in scrap_rows(doc):
		bom_row = d.bom_secondary_item and frappe.db.get_value(
			"BOM Secondary Item", d.bom_secondary_item, ["stock_qty", "parent"], as_dict=True
		)
		if not bom_row:
			continue
		bom_qty = flt(frappe.db.get_value("BOM", bom_row.parent, "quantity")) or 1
		d.standard_scrap_qty = flt(flt(bom_row.stock_qty) * fg_qty / bom_qty, 3)


def row_batches(row):
	"""[(batch_no, qty)] for a stock row (bundle is set in db after submit)."""
	bundle = row.serial_and_batch_bundle or frappe.db.get_value(
		row.doctype, row.name, "serial_and_batch_bundle"
	)
	if bundle:
		return frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": bundle, "batch_no": ["is", "set"]},
			fields=["batch_no", "qty"],
			as_list=True,
		)
	return [(row.batch_no, row.get("transfer_qty") or row.get("stock_qty"))] if row.batch_no else []


def output_batches(doc):
	return {b for d in doc.items if d.is_finished_item for b, _q in row_batches(d)}


def set_batch_orders(doc):
	"""Output batch remembers its Work Order, Production Plan and Sales Order."""
	if not doc.work_order:
		return
	wo = frappe.db.get_value("Work Order", doc.work_order, ["sales_order", "production_plan"], as_dict=True)
	so = wo.sales_order
	if not so and wo.production_plan:  # sub-assembly WOs carry no SO; use the plan's if it has one
		sos = frappe.get_all("Production Plan Sales Order", {"parent": wo.production_plan}, pluck="sales_order")
		so = sos[0] if len(set(sos)) == 1 else None
	for batch in output_batches(doc):
		# keep the first order's details when several Work Orders share a batch number;
		# no reference_name, as ERPNext would delete the shared batch on cancel
		current = frappe.db.get_value("Batch", batch, ["work_order", "sales_order", "production_plan"], as_dict=True)
		values = {"work_order": doc.work_order, "sales_order": so, "production_plan": wo.production_plan}
		missing = {k: v for k, v in values.items() if v and not current.get(k)}
		if missing:
			frappe.db.set_value("Batch", batch, missing)


def link_batches(doc):
	sources = []
	for d in doc.items:
		if d.s_warehouse and not d.is_finished_item and not d.secondary_item_type:
			sources += [(b, d.item_code, abs(flt(q))) for b, q in row_batches(d)]
	if not sources:
		return
	for batch in output_batches(doc):
		for src, item_code, qty in sources:
			frappe.get_doc({
				"doctype": "Batch Source", "parenttype": "Batch", "parentfield": "source_batches",
				"parent": batch, "source_batch": src, "item_code": item_code, "qty": qty,
				"stock_entry": doc.name, "idx": 99,
			}).db_insert()
		refresh_trace_lot(batch)


def refresh_trace_lot(batch):
	"""Trace lot = origin batches (RM / purchased SFG) of all sources."""
	srcs = frappe.get_all("Batch Source", {"parent": batch, "parenttype": "Batch"}, pluck="source_batch")
	lots = set()
	for src in srcs:
		lot = frappe.db.get_value("Batch", src, "trace_lot")
		lots.update([x.strip() for x in lot.split(",")] if lot else [src])
	frappe.db.set_value("Batch", batch, "trace_lot", ", ".join(sorted(lots)) or None)
