# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from pprint import pprint
from frappe.model.document import Document
from erpnext.stock.doctype.stock_entry.stock_entry import get_additional_costs

class ShiftRunSummary(Document):
	def on_submit(self):
		first_start_time = self.get_first_start_time()
		last_end_time = self.get_last_end_time()
		good_qty = self.get_good_qty()
		total_qty = self.get_total_qty()

		default_scrap_warehouse = frappe.db.sql("SELECT *  FROM `tabWarehouse` WHERE `default_scrap_warehouse` = 1", as_dict=1)
		if len(default_scrap_warehouse) == 0:
			default_scrap_warehouse = None
		else:
			default_scrap_warehouse = default_scrap_warehouse[0]["name"]

		prod_order = frappe.get_doc("Production Order", self.production_order)
		bom = frappe.get_doc("BOM", prod_order.bom_no)

		boms = {}
		for bm in bom.items:
			boms[bm.item_code] = {"scrap": bm.scrap}

		transfer = frappe.new_doc("Stock Entry")
		transfer.purpose = "Material Transfer for Manufacture"
		transfer.production_order = self.production_order
		transfer.company = prod_order.company
		transfer.from_bom = 1
		transfer.bom_no = prod_order.bom_no
		transfer.use_multi_level_bom = prod_order.use_multi_level_bom
		transfer.fg_completed_qty = total_qty
		transfer.to_warehouse = prod_order.wip_warehouse
		transfer.shift_run_summary = self.name

		for part in self.parts:
			raw_matl = transfer.get_bom_raw_materials(part.good_parts_qty + part.scrap_parts_qty)
			for rm in raw_matl.values():
				rm["batch"] = part.batch
			transfer.add_to_stock_entry_detail(raw_matl)


		transfer.save()
		transfer.submit()

		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"from_time": first_start_time,
			"to_time": last_end_time,
			"for_manufacturing": 1,
			"production_order": self.production_order,
			"operation": prod_order.operations[0].operation,
			"workstation": prod_order.operations[0].workstation,
			"completed_qty": total_qty,
			"shift_run_summary": self.name
		})
		time_log.save()
		time_log.submit()

		manufacture = frappe.new_doc("Stock Entry")
		manufacture.shift_run_summary = self.name
		manufacture.purpose = "Manufacture"
		manufacture.production_order = self.production_order
		manufacture.company = prod_order.company
		manufacture.from_bom = 1
		manufacture.bom_no = prod_order.bom_no
		manufacture.use_multi_level_bom = prod_order.use_multi_level_bom
		manufacture.fg_completed_qty = total_qty
		manufacture.from_warehouse = prod_order.wip_warehouse
		manufacture.to_warehouse = prod_order.fg_warehouse
		additional_costs = get_additional_costs(prod_order, fg_qty=total_qty)
		manufacture.set("additional_costs", additional_costs)

		se_parts = {}
		se_scrap_parts = {}
		for part in self.parts:
			raw_matl = transfer.get_bom_raw_materials(part.good_parts_qty + part.scrap_parts_qty)

			scrap_matl = {}
			for key, rm in raw_matl.items():

				rm["batch"] = part.batch
				rm["from_warehouse"] = prod_order.wip_warehouse
				rm["to_warehouse"] = ""


				if key in scrap_matl:
					scrap_matl[key]["qty"] += rm['qty'] * (boms[key]['scrap'] / 100)
				else:
					scrap_matl[key] = {"qty": rm['qty'] * (boms[key]['scrap'] / 100),
						"from_warehouse": "",
						"to_warehouse": default_scrap_warehouse,
						"description": rm.description,
						"uom": rm.uom,
						"batch": part.batch,
						"item_name": rm.item_name,
						"stock_uom": rm.uom,
						"expense_account": rm.expense_account,
						"cost_center": rm.cost_center,
						"scrap": 1
					}

				item = frappe.get_doc("Item", part.part)

				if (part.part in se_parts):
					se_parts[part.part]["qty"] += part.good_parts_qty
				else:
					se_parts[part.part] = {
						"item_name": part.part,
						"qty": part.good_parts_qty,
						"from_warehouse": "",
						"to_warehouse": prod_order.fg_warehouse,
						"description": item.description,
						"stock_uom": item.stock_uom,
						"item_name": part.part,
						"expense_account": item.expense_account,
						"cost_center": item.buying_cost_center
					}

				if (part.part in se_scrap_parts):
					se_scrap_parts[part.part]["qty"] += part.scrap_parts_qty
				else:
					se_scrap_parts[part.part] = {
						"item_name": part.part,
						"qty": part.scrap_parts_qty,
						"from_warehouse": "",
						"to_warehouse": default_scrap_warehouse,
						"description": item.description,
						"stock_uom": item.stock_uom,
						"item_name": part.part,
						"expense_account": item.expense_account,
						"cost_center": item.buying_cost_center,
						"scrap": 1
					}
			manufacture.add_to_stock_entry_detail(raw_matl)
			manufacture.add_to_stock_entry_detail(scrap_matl)

		manufacture.add_to_stock_entry_detail(se_parts, prod_order.bom_no)
		manufacture.add_to_stock_entry_detail(se_scrap_parts, prod_order.bom_no)

		for idx, item in enumerate(manufacture.items):
			if item.transfer_qty == 0:
				del manufacture.items[idx]

		manufacture.save()
		manufacture.submit()



	def on_cancel(self):
		for manufactures in frappe.get_all("Stock Entry", ["name"], {"purpose":"Manufacture", "shift_run_summary": self.name}):
			doc = frappe.get_doc("Stock Entry", manufactures.name)
			doc.cancel()
			doc.delete()

		for time_log in frappe.get_all("Time Log", ["name"], {"shift_run_summary": self.name}):
			doc = frappe.get_doc("Time Log", time_log.name)
			doc.cancel()
			doc.delete()

		for transfers in frappe.get_all("Stock Entry", ["name"], {"purpose":"Material Transfer for Manufacture", "shift_run_summary": self.name}):
			doc = frappe.get_doc("Stock Entry", transfers.name)
			doc.cancel()
			doc.delete()



	def get_first_start_time(self):
		first_start_time = self.parts[0].start_time
		for item in self.parts:
			if first_start_time > item.start_time:
				first_start_time = item.start_time
		for item in self.downtime:
			if first_start_time > item.downtime_start:
				first_start_time = item.downtime_start
		return first_start_time

	def get_last_end_time(self):
		last_end_time = self.parts[0].end_time
		for item in self.parts:
			if last_end_time < item.end_time:
				last_end_time = item.end_time
		for item in self.downtime:
			if last_end_time < item.downtime_end:
				last_end_time = item.downtime_end
		return last_end_time

	def get_good_qty(self):
		qty = 0
		for item in self.parts:
			qty += item.good_parts_qty
		return qty

	def get_total_qty(self):
		qty = 0
		for item in self.parts:
			qty += item.good_parts_qty + item.scrap_parts_qty
		return qty
