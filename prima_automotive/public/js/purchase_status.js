// No purchase invoices at Prima: show receiving status, never "To Bill".
// 90% of the PO qty or more counts as received (receipts vary +-10%).
(() => {
	const RECEIVED_AT = 90;
	const pr = frappe.listview_settings["Purchase Receipt"];
	if (pr && !pr.prima_status) {
		const base = pr.get_indicator;
		pr.prima_status = true;
		pr.add_fields = [...(pr.add_fields || []), "po_received_percent"];
		pr.get_indicator = (doc) => {
			const ind = base(doc);
			if (ind && ["To Bill", "Partly Billed", "Completed"].includes(ind[0]) && doc.docstatus === 1) {
				const pct = flt(doc.po_received_percent);
				if (pct && pct < RECEIVED_AT) {
					return [__("Partially Received"), "yellow", `po_received_percent,<,${RECEIVED_AT}|docstatus,=,1`];
				}
				return [__("Received"), "green", "docstatus,=,1|is_return,=,0"];
			}
			return ind;
		};
	}

	const po = frappe.listview_settings["Purchase Order"];
	if (po && !po.prima_status) {
		const base = po.get_indicator;
		po.prima_status = true;
		po.get_indicator = (doc) => {
			const ind = base(doc);
			if (doc.docstatus === 1 && doc.status === "Closed" && flt(doc.per_received) >= RECEIVED_AT) {
				return [__("Completed"), "green", `status,=,Closed|per_received,>=,${RECEIVED_AT}`];
			}
			if (!ind || doc.docstatus !== 1 || ["Closed", "On Hold", "Delivered"].includes(doc.status)) return ind;
			if (!flt(doc.per_received)) {
				return [__("To Receive"), "orange", "per_received,=,0|status,!=,Closed|docstatus,=,1"];
			}
			if (flt(doc.per_received) < RECEIVED_AT) {
				return [__("Partially Received"), "yellow", `per_received,>,0|per_received,<,${RECEIVED_AT}|status,!=,Closed|docstatus,=,1`];
			}
			return [__("Received"), "green", `per_received,>=,${RECEIVED_AT}|status,!=,Closed|docstatus,=,1`];
		};
	}
})();
