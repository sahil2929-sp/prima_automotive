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
	missing = [_(label) for field, label in (("machine_no", "Machine No."), ("operator_name", "Operator Name"))
		if not (doc.get(field) or "").strip()]
	if missing:
		frappe.throw(_("Please enter {0} for this production entry.").format(" and ".join(missing)),
			title=_("Missing Details"))


def set_output_batch(doc):
	"""Show the output batch on the draft: STAGE/FY/<running no of main input batch>.
	Daily entries of one Work Order keep adding to that Work Order's batch."""
	main_input = None
	for row in doc.items:
		if not row.is_finished_item or row.batch_no or row.serial_and_batch_bundle:
			continue
		if not frappe.db.get_value("Item", row.item_code, "has_batch_no"):
			continue
		name = work_order_batch(row.item_code, doc.work_order)
		if not name:
			main_input = main_input or main_input_batch(doc)
			if not main_input:
				return
			name = batch_name_for(row.item_code, main_input, doc)
		if not name:
			continue
		if not frappe.db.exists("Batch", name):
			# no reference yet: ERPNext deletes referenced batches with a deleted draft and fails;
			# set_batch_orders adds it on submit, an unused batch is reused by the next draft
			frappe.get_doc({"doctype": "Batch", "batch_id": name, "item": row.item_code}).insert(ignore_permissions=True)
		row.use_serial_batch_fields = 1
		row.batch_no = name


def work_order_batch(item_code, work_order):
	"""Batch already made for this item by an earlier entry of the same Work Order."""
	return work_order and frappe.db.get_value(
		"Batch", {"item": item_code, "work_order": work_order}, "name", order_by="creation asc"
	)


def main_input_batch(doc):
	"""Input batch with the largest qty; on a draft without input batches,
	the batches moved to WIP by this Work Order's transfers."""
	rows = [d for d in doc.items if d.s_warehouse and not d.is_finished_item and not d.secondary_item_type]
	inputs = [(b, abs(flt(q))) for d in rows for b, q in row_batches(d) if b]
	if not inputs and doc.work_order:
		transfers = frappe.get_all("Stock Entry", {"work_order": doc.work_order, "docstatus": 1,
			"purpose": "Material Transfer for Manufacture"}, pluck="name")
		items = {d.item_code for d in rows}
		for se in transfers:
			for d in frappe.get_doc("Stock Entry", se).items:
				if d.item_code in items:
					inputs += [(b, abs(flt(q))) for b, q in row_batches(d) if b]
	if not inputs:  # no transfer (later stages): the batch FIFO will pick at submit
		inputs = [(b, q) for d in rows for b, q in fifo_batches(d)]
	return inputs and max(inputs, key=lambda x: x[1])[0]


def fifo_batches(row):
	from erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle import get_auto_batch_nos

	if not frappe.db.get_value("Item", row.item_code, "has_batch_no"):
		return []
	picked = get_auto_batch_nos(frappe._dict(item_code=row.item_code, warehouse=row.s_warehouse,
		qty=row.transfer_qty or row.qty, based_on="FIFO"))
	return [(b.batch_no, flt(b.qty)) for b in picked or [] if b.get("batch_no")]


def batch_name_for(item_code, main_input, doc):
	"""First free name; an unused batch made for an earlier draft is reused."""
	from erpnext.accounts.utils import get_fiscal_year

	parts = main_input.split("/")
	prefix = (frappe.db.get_value("Item", item_code, "batch_number_series") or "").split("/")[0].strip(".")
	if len(parts) < 3 or not prefix:
		return None  # input not in PREFIX/FY/NO format
	fy = get_fiscal_year(doc.posting_date, company=doc.company)[0]
	base = name = f"{prefix}/{fy}/{'/'.join(parts[2:])}"
	n = 1
	while frappe.db.exists("Batch", name) and not unused_batch(name, item_code, doc.name):
		n += 1
		name = f"{base}-{n}"
	return name


def unused_batch(name, item_code, entry):
	"""Same item, no stock moved, and not held by another draft entry."""
	return (
		frappe.db.get_value("Batch", name, "item") == item_code
		and not frappe.db.exists("Serial and Batch Entry", {"batch_no": name, "docstatus": 1})
		and not frappe.db.exists("Stock Entry Detail", {"batch_no": name, "docstatus": 0, "parent": ["!=", entry]})
	)


def on_submit(doc, method=None):
	if doc.purpose == "Manufacture":
		rename_output_batches(doc)
		link_batches(doc)
		set_batch_orders(doc)


def rename_output_batches(doc):
	"""BRD format: STAGE/FY/<running no of main input batch>, e.g. RM/26-27/00001 -> CT/26-27/00001.
	A second batch from the same input gets -2, -3 ..."""
	from erpnext.accounts.utils import get_fiscal_year

	inputs = [
		(b, abs(flt(q)))
		for d in doc.items
		if d.s_warehouse and not d.is_finished_item and not d.secondary_item_type
		for b, q in row_batches(d)
	]
	if not inputs:
		return
	main_input = max(inputs, key=lambda x: x[1])[0]
	parts = main_input.split("/")
	if len(parts) < 3:
		return  # input not in PREFIX/FY/NO format
	running_no = "/".join(parts[2:])
	fy = get_fiscal_year(doc.posting_date, company=doc.company)[0]

	for batch in output_batches(doc):
		ref = frappe.db.get_value("Batch", batch, ["reference_doctype", "reference_name", "item"], as_dict=True)
		if ref.reference_doctype != "Stock Entry" or ref.reference_name != doc.name:
			continue  # batch chosen by user, not auto-created here
		series = frappe.db.get_value("Item", ref.item, "batch_number_series") or ""
		prefix = series.split("/")[0].strip(".")
		if not prefix:
			continue
		base = new = f"{prefix}/{fy}/{running_no}"
		n = 1
		while frappe.db.exists("Batch", new) and new != batch:
			n += 1
			new = f"{base}-{n}"
		if new != batch:
			frappe.rename_doc("Batch", batch, new, force=True, show_alert=False)
			frappe.db.set_value("Batch", new, "batch_id", new)


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
		frappe.db.set_value("Batch", batch, {"work_order": doc.work_order, "sales_order": so,
			"production_plan": wo.production_plan, "reference_doctype": "Stock Entry", "reference_name": doc.name})


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
