// Target = item's default warehouse; each input row = its BOM / item default warehouse
const set_wo_warehouses = frappe.utils.debounce((frm) => {
	// wait for ERPNext to reload required items, then correct them
	frappe.after_ajax(async () => {
		if (!frm.doc.production_item || !frm.doc.company || frm.doc.docstatus) return;
		const wh = await frappe.xcall("prima_automotive.overrides.work_order.get_wo_warehouses", {
			item_code: frm.doc.production_item,
			company: frm.doc.company,
			bom_no: frm.doc.bom_no,
		});
		if (wh.target) frm.set_value("fg_warehouse", wh.target);
		// only Cutting transfers RM to WIP; later stages already sit in WIP
		if (frm.is_new()) frm.set_value("skip_transfer", wh.skip_transfer);
		// set header without its handler, which would copy one value into every row
		frm.doc.source_warehouse = wh.source || "";
		frm.refresh_field("source_warehouse");
		for (const row of frm.doc.required_items || []) {
			const src = wh.rows[row.item_code];
			if (src && row.source_warehouse !== src) {
				await frappe.model.set_value(row.doctype, row.name, "source_warehouse", src);
			}
		}
	});
}, 300);

frappe.ui.form.on("Work Order", {
	production_item: set_wo_warehouses,
	bom_no: set_wo_warehouses,
});
