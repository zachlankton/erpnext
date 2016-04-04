# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShiftRunSummary(Document):
	def on_submit(self):
		first_start_time = self.get_first_start_time()
		last_end_time = self.get_last_end_time()
		
		prod_order = frappe.get_doc("Production Order", self.production_order)
		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"from_time": first_start_time,
			"to_time": last_end_time,
			"for_manufacturing": 1,
			"production_order": self.production_order,
			"operation": prod_order.operations[0].operation,
			"workstation": "prod_order.operations[0].workstation
		})
		time_log.save()
	
	def get_first_start_time(self):
		first_start_time self.parts[0].start_time
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
