import frappe

from prima_automotive.overrides.stock_entry import row_batches


RECEIVED_AT = 90  # % of PO qty; receipts vary +-10%, so 90% completes the PO


def on_submit(doc, method=None):
	set_po_received_percent(doc)
	set_batch_supplier(doc)
	complete_purchase_orders(doc)


def before_cancel(doc, method=None):
	"""ERPNext won't cancel a receipt against a closed PO: reopen the ones we closed."""
	for po in linked_pos(doc):
		if frappe.db.get_value("Purchase Order", po, "status") == "Closed":
			frappe.get_doc("Purchase Order", po).update_status("Submitted")


def on_cancel(doc, method=None):
	complete_purchase_orders(doc)


def linked_pos(doc):
	return {d.purchase_order for d in doc.items if d.purchase_order}


def complete_purchase_orders(doc):
	"""PO with 90%+ received is complete: close it so nothing stays pending."""
	for po in linked_pos(doc):
		po_doc = frappe.get_doc("Purchase Order", po)
		if po_doc.docstatus == 1 and po_doc.status != "Closed" and po_doc.per_received >= RECEIVED_AT:
			po_doc.update_status("Closed")


def set_po_received_percent(doc):
	"""PO received % after this receipt (lowest if the receipt covers several POs)."""
	pos = linked_pos(doc)
	if pos:
		pct = min(frappe.db.get_value("Purchase Order", po, "per_received") or 0 for po in pos)
		doc.db_set("po_received_percent", pct, update_modified=False)


def set_batch_supplier(doc):
	"""Purchased batch (RM or SFG) is an origin lot; keep supplier on it."""
	for d in doc.items:
		# bundle may be saved only in db at this point, row_batches reads it from there
		for b in {b for b, _q in row_batches(d) if b}:
			frappe.db.set_value("Batch", b, {"supplier": doc.supplier, "trace_lot": b})
