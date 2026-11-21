import frappe
from frappe import _
from frappe.utils import flt


def validate(doc, method=None):
	if doc.purpose == "Manufacture":
		set_standard_scrap_qty(doc)


def before_submit(doc, method=None):
	if doc.purpose == "Manufacture" and scrap_rows(doc) and not doc.get("actual_scrap_entered"):
		frappe.throw(
			_("Update scrap rows with the actual shop-floor qty and tick <b>Actual Scrap Qty Entered</b>."),
			title=_("Actual Scrap Required"),
		)


def on_submit(doc, method=None):
	if doc.purpose == "Manufacture":
		rename_output_batches(doc)
		link_batches(doc)


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
		d.standard_scrap_qty = flt(bom_row.stock_qty) * fg_qty / bom_qty


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
