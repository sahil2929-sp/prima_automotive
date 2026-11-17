import frappe


def on_submit(doc, method=None):
	"""Purchased batch (RM or SFG) is an origin lot; keep supplier on it."""
	for d in doc.items:
		batches = [d.batch_no] if d.batch_no else []
		if d.serial_and_batch_bundle:
			batches = frappe.get_all("Serial and Batch Entry", {"parent": d.serial_and_batch_bundle}, pluck="batch_no")
		for b in filter(None, batches):
			frappe.db.set_value("Batch", b, {"supplier": doc.supplier, "trace_lot": b})
