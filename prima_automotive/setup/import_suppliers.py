"""Import the client's supplier sheet (Supplier + Contact + Address).

bench --site <site> execute prima_automotive.setup.import_suppliers.run --kwargs '{"path": "<xlsx>"}'
"""

import frappe


def read_rows(path):
	from openpyxl import load_workbook

	ws = load_workbook(path, data_only=True, read_only=True).active
	rows = [r for r in ws.iter_rows(values_only=True) if any(v is not None for v in r)]
	head = [str(h).strip() for h in rows[0]]
	return [{k: (str(v).strip() if v is not None else "") for k, v in zip(head, r)} for r in rows[1:]]


def valid_gstin(gstin):
	from india_compliance.gst_india.utils import validate_gstin

	try:
		return validate_gstin(gstin) if gstin else None
	except frappe.ValidationError:
		return None


def set_primary(supplier, contact, address=None):
	values = {"supplier_primary_contact": contact.name, "mobile_no": contact.mobile_no}
	if address:
		values["supplier_primary_address"] = address.name
	frappe.db.set_value("Supplier", supplier, values)


def run(path):
	created, skipped, bad_gstin = [], [], []
	for row in read_rows(path):
		name = row["Supplier Name"]
		if frappe.db.exists("Supplier", {"supplier_name": name}):
			skipped.append(name)
			continue
		gstin = valid_gstin(row["Tax ID"])
		if row["Tax ID"] and not gstin:
			bad_gstin.append(f"{name}: {row['Tax ID']}")

		supplier = frappe.get_doc({
			"doctype": "Supplier", "supplier_name": name,
			"supplier_group": row["Supplier Group"] or "Local", "country": row["Country"] or "India",
			"default_price_list": row["Price List"] or None,
			"gstin": gstin, "gst_category": "Registered Regular" if gstin else "Unregistered",
		}).insert()
		link = [{"link_doctype": "Supplier", "link_name": supplier.name}]

		mobile = row["Mobile No (Contact)"]
		contact = frappe.get_doc({
			"doctype": "Contact", "first_name": row["First Name (Contact)"] or name,
			"company_name": name, "is_primary_contact": 1, "links": link,
			"phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1}] if mobile else [],
		}).insert()

		address = None
		if row["Address Line 1 (Address)"]:
			address = frappe.get_doc({
				"doctype": "Address", "address_title": row["Address Title (Address)"] or name,
				"address_type": row["Address Type (Address)"] or "Billing",
				"address_line1": row["Address Line 1 (Address)"], "address_line2": row["Address Line 2 (Address)"],
				"city": row["City/Town (Address)"], "state": row["State/Province (Address)"],
				"country": row["Country (Address)"] or "India", "pincode": row["Postal Code (Address)"] or None,
				"gstin": gstin, "is_primary_address": 1, "is_shipping_address": 1, "links": link,
			}).insert()
		set_primary(supplier.name, contact, address)
		created.append(supplier.name)

	frappe.db.commit()
	print(f"created {len(created)}, skipped {len(skipped)}, invalid GSTIN {len(bad_gstin)}")
	return {"created": created, "skipped": skipped, "invalid_gstin": bad_gstin}
