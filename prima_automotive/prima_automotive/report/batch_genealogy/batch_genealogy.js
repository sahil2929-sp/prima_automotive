frappe.query_reports["Batch Genealogy"] = {
	filters: [
		{ fieldname: "batch", label: __("Batch"), fieldtype: "Link", options: "Batch", reqd: 1 },
		{
			fieldname: "direction", label: __("Direction"), fieldtype: "Select", reqd: 1,
			options: ["Backward", "Forward"], default: "Backward",
			description: __("Backward: FG to RM. Forward: RM to FG."),
		},
	],
	tree: true,
	initial_depth: 10,
};
