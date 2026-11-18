// Warehouses come from item defaults; sub-assembly rows load without "Get Sub Assembly Items"
function set_sub_assembly_warehouse(frm) {
	if (frm.doc.docstatus || frm.doc.sub_assembly_warehouse || !frm.doc.company) return Promise.resolve();
	return frappe
		.xcall("prima_automotive.overrides.production_plan.get_wip_warehouse", { company: frm.doc.company })
		.then((wh) => wh && frm.set_value("sub_assembly_warehouse", wh));
}

const auto_sub_assembly = frappe.utils.debounce((frm) => {
	frappe.after_ajax(async () => {
		const rows = frm.doc.po_items || [];
		if (frm.doc.docstatus || !rows.length) return;
		if (!rows.every((r) => r.item_code && r.bom_no && r.planned_qty)) return;
		await set_sub_assembly_warehouse(frm);
		frm.trigger("get_sub_assembly_items");
	});
}, 600);

frappe.ui.form.on("Production Plan", {
	onload: set_sub_assembly_warehouse,
	company: set_sub_assembly_warehouse,
	get_items: auto_sub_assembly,
	combine_items: auto_sub_assembly,
	po_items_remove: auto_sub_assembly,
});

frappe.ui.form.on("Production Plan Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code || !frm.doc.company) return;
		frappe
			.xcall("prima_automotive.overrides.work_order.get_item_warehouse", {
				item_code: row.item_code,
				company: frm.doc.company,
			})
			.then((wh) => wh && frappe.model.set_value(cdt, cdn, "warehouse", wh));
	},
	bom_no: auto_sub_assembly,
	planned_qty: auto_sub_assembly,
});
