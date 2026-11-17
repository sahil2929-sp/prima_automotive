frappe.query_reports["Stage-wise WIP"] = {
	filters: [
		{ fieldname: "product", label: __("Product"), fieldtype: "Link", options: "Item",
			get_query: () => ({ filters: { item_group: "Finished Goods" } }) },
		{ fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "shortfall" && data && data.shortfall > 0) {
			value = `<span style="color: var(--red-600); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
