import frappe
from frappe import _
from frappe import scrub
from frappe.utils import flt

SFG_PARENT = "Semi Finished Goods"
FG_GROUP = "Finished Goods"
RM_GROUP = "Raw Material"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	stages = frappe.get_all("Item Group", {"parent_item_group": SFG_PARENT}, pluck="name", order_by="lft")
	return get_columns(stages), get_data(filters, stages)


def get_columns(stages):
	cols = [
		{"label": _("Product"), "fieldname": "product", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Product Name"), "fieldname": "product_name", "fieldtype": "Data", "width": 180},
		{"label": _("RM Stock"), "fieldname": "rm_qty", "fieldtype": "Float", "width": 100},
	]
	cols += [{"label": _(s), "fieldname": scrub(s), "fieldtype": "Float", "width": 105} for s in stages]
	cols += [
		{"label": _("Finished Goods"), "fieldname": "fg_qty", "fieldtype": "Float", "width": 115},
		{"label": _("Open SO Qty"), "fieldname": "open_so_qty", "fieldtype": "Float", "width": 110},
		{"label": _("FG Shortfall"), "fieldname": "shortfall", "fieldtype": "Float", "width": 110},
	]
	return cols


def get_data(filters, stages):
	fg_filters = {"item_group": FG_GROUP, "disabled": 0}
	if filters.product:
		fg_filters["name"] = filters.product
	products = frappe.get_all("Item", fg_filters, ["name", "item_name"], order_by="name")
	stock, group_of, children, open_so = get_stock(filters), get_item_groups(), get_bom_children(), get_open_so()

	data = []
	for p in products:
		row = frappe._dict(product=p.name, product_name=p.item_name, rm_qty=0, fg_qty=stock.get(p.name, 0))
		for s in stages:
			row[scrub(s)] = 0
		for code in chain_items(p.name, children):
			group = group_of.get(code)
			if group in stages:
				row[scrub(group)] += stock.get(code, 0)
			elif group == RM_GROUP:
				row.rm_qty += stock.get(code, 0)
		row.open_so_qty = open_so.get(p.name, 0)
		row.shortfall = max(row.open_so_qty - row.fg_qty, 0)
		data.append(row)
	return data


def chain_items(item, children, seen=None):
	"""All items below `item` in its default BOM tree."""
	seen = seen if seen is not None else set()
	for child in children.get(item, []):
		if child not in seen:
			seen.add(child)
			chain_items(child, children, seen)
	return seen


def get_bom_children():
	rows = frappe.db.sql(
		"""select bom.item, bi.item_code from `tabBOM` bom
		join `tabBOM Item` bi on bi.parent = bom.name
		where bom.is_default = 1 and bom.is_active = 1 and bom.docstatus = 1""",
		as_dict=True,
	)
	children = {}
	for r in rows:
		children.setdefault(r.item, []).append(r.item_code)
	return children


def get_item_groups():
	return dict(frappe.get_all("Item", fields=["name", "item_group"], as_list=True))


def get_stock(filters):
	cond, values = "", {}
	if filters.warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"])
		cond = "and wh.lft >= %(lft)s and wh.rgt <= %(rgt)s"
		values = {"lft": lft, "rgt": rgt}
	rows = frappe.db.sql(
		f"""select bin.item_code, sum(bin.actual_qty) from `tabBin` bin
		join `tabWarehouse` wh on wh.name = bin.warehouse
		where 1=1 {cond} group by bin.item_code""",
		values,
	)
	return {code: flt(qty) for code, qty in rows}


def get_open_so():
	rows = frappe.db.sql(
		"""select soi.item_code, sum((soi.qty - soi.delivered_qty) * soi.conversion_factor)
		from `tabSales Order Item` soi join `tabSales Order` so on so.name = soi.parent
		where so.docstatus = 1 and so.status not in ('Closed', 'Completed', 'On Hold')
			and soi.qty > soi.delivered_qty
		group by soi.item_code"""
	)
	return {code: flt(qty) for code, qty in rows}
