// Copyright (c) 2026, ParaLogic and contributors
// For license information, please see license.txt

frappe.ui.form.on("PowerBI Report Source", {
	refresh(frm) {
		frm.trigger("fetch_report_filters");
		if (frm.is_new()) {
			if (!frm.doc.user) {
				frm.set_value("user", frappe.session.user);
			}
		} else {
			frm.add_custom_button(__("View Report"), () => frm.trigger("view_report"));
		}
	},

	async view_report(frm) {
		if (frm.is_new() || !frm.doc.report || !frm.doc.name) {
			return;
		}

		if (frm.doc.report_type != "Report Builder") {
			frappe.route_options = await frm.events.get_parsed_filters(frm) || {};
			frappe.set_route("query-report", frm.doc.report);
		}
	},

	get_parsed_filters(frm) {
		return frappe.xcall(
			"pbi_integration.powerbi_integration.doctype.powerbi_report_source.powerbi_report_source.get_parsed_filters",
			{report_source: frm.doc.name},
		);
	},

	report(frm) {
		frm.set_value("filters", "");
		frm.trigger("fetch_report_filters");
	},

	fetch_report_filters(frm) {
		if (
			frm.doc.report
			&& frm.doc.report_type !== "Report Builder"
			&& frm.script_setup_for !== frm.doc.report
		) {
			frappe.call({
				method: "frappe.desk.query_report.get_script",
				args: {
					report_name: frm.doc.report,
				},
				callback: function (r) {
					frappe.dom.eval(r.message.script || "");
					frm.script_setup_for = frm.doc.report;
					frm.trigger("show_filters");
				},
			});
		} else {
			frm.trigger("show_filters");
		}
	},

	async show_filters(frm) {
		if (!frm.doc.report) {
			return;
		}

		let wrapper = $(frm.get_field("filters_display").wrapper);
		wrapper.empty();

		let reference_report = frappe.query_reports[frm.doc.report];
		if (!reference_report || !reference_report.filters) {
			reference_report = await frappe.model.with_doc("Report", frm.doc.report);
		}

		if (
			frm.doc.report_type === "Custom Report" ||
			(frm.doc.report_type !== "Report Builder" &&
				reference_report &&
				reference_report.filters)
		) {
			// make a table to show filters
			var table = $(
				'<table class="table table-bordered" style="cursor:pointer; margin:0px;"><thead>\
				<tr><th style="width: 50%">' +
					__("Filter") +
					"</th><th>" +
					__("Value") +
					"</th></tr>\
				</thead><tbody></tbody></table>"
			).appendTo(wrapper);
			$('<p class="text-muted small">' + __("Click table to edit") + "</p>").appendTo(
				wrapper
			);

			let filters = {};
			let dialog;
			let report_filters;
			let report_name;

			if (
				frm.doc.report_type === "Custom Report"
				&& reference_report
				&& reference_report.filters
			) {
				if (frm.doc.filters) {
					filters = JSON.parse(frm.doc.filters);
				} else {
					frappe.db.get_value("Report", frm.doc.report, "json", (r) => {
						if (r && r.json) {
							filters = JSON.parse(r.json).filters || {};
						}
					});
				}

				report_filters = frappe.query_reports[frm.doc.reference_report].filters;
				report_name = frm.doc.reference_report;
			} else {
				filters = JSON.parse(frm.doc.filters || "{}");
				report_filters = reference_report.filters;
			}

			frm.doc.filter_meta = report_filters && report_filters.length > 0 ? JSON.stringify(report_filters) : "";
			frm.refresh_field("filter_meta");

			let report_filters_list = [];
			$.each(report_filters, function (key, val) {
				// Remove break fieldtype from the filters
				if (val.fieldtype != "Break") {
					if (val.fieldtype === "MultiSelectList") {
						val.get_data = (txt) => {
							if (!dialog || !val.options) return [];

							if (Array.isArray(val.options)) return val.options;

							const doctype_link =
								frappe.scrub(val.options) === val.options
									? dialog.get_value(val.options)
									: val.options;

							return doctype_link
								? frappe.db.get_link_options(doctype_link, txt)
								: [];
						};
					}
					report_filters_list.push(val);
				}
			});
			report_filters = report_filters_list;

			const mandatory_css = {
				"background-color": "var(--error-bg)",
				"font-weight": "bold",
			};

			report_filters.forEach((f) => {
				const css = f.reqd ? mandatory_css : {};
				const row = $("<tr></tr>").appendTo(table.find("tbody"));
				$("<td>" + f.label + "</td>").appendTo(row);
				$("<td>" + frappe.format(filters[f.fieldname], f) + "</td>")
					.css(css)
					.appendTo(row);
			});

			// remove mandatory but hidden filters from dialog
			const dialog_filter_fields = report_filters.filter(
				(f) => !(f.hidden == 1 && f.reqd == 1)
			);
			table.on("click", function () {
				dialog = new frappe.ui.Dialog({
					title: __("Edit Filters"),
					fields: dialog_filter_fields,
					primary_action: function () {
						var values = this.get_values();
						if (values) {
							this.hide();
							frm.set_value("filters", JSON.stringify(values));
							frm.trigger("show_filters");
						}
					},
				});
				dialog.show();

				// add filters defined in onload event of report
				if (reference_report.onload) {
					frappe.query_report = new frappe.views.QueryReport({
						filters: dialog.fields_list,
					});
					reference_report.onload(frappe.query_report);
				}

				dialog.doc = dialog.doc || {};
				dialog.fields_list.forEach((f) => (f.doc = dialog.doc));

				dialog.set_values(filters);
			});

			// populate dynamic date field selection
			let date_fields = report_filters
				.filter((df) => df.fieldtype === "Date")
				.map((df) => ({ label: df.label, value: df.fieldname }));

			frm.set_df_property("from_date_field", "options", date_fields);
			frm.set_df_property("to_date_field", "options", date_fields);
			frm.toggle_display("dynamic_report_filters_section", date_fields.length > 0);
		} else {
			frm.set_value("filter_meta", "");
		}
	},
});
