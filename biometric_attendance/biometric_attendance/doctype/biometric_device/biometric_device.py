import frappe
from frappe.model.document import Document
from zk import ZK, const
import json
from datetime import datetime
from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

class BiometricDevice(Document):
    def validate(self):
        self.validate_ip_address()
    
    def validate_ip_address(self):
        # Basic IP address validation
        try:
            parts = self.ip_address.split('.')
            if len(parts) != 4:
                frappe.throw("Invalid IP Address format")
            for part in parts:
                if not 0 <= int(part) <= 255:
                    frappe.throw("Invalid IP Address format")
        except ValueError:
            frappe.throw("Invalid IP Address format")

    def get_attendance_logs(self):
        """Fetch attendance logs from the device"""
        zk = ZK(self.ip_address, port=self.port, timeout=30)
        conn = None
        try:
            conn = zk.connect()
            conn.disable_device()
            attendance_logs = conn.get_attendance()
            
            # Convert attendance logs to list of dicts
            logs = []
            for attendance in attendance_logs:
                log = {
                    'user_id': attendance.user_id,
                    'timestamp': attendance.timestamp,
                    'punch': attendance.punch,
                    'status': attendance.status,
                    'uid': attendance.uid
                }
                logs.append(log)
            
            if self.clear_from_device_on_fetch:
                conn.clear_attendance()
            
            return logs
        
        except Exception as e:
            frappe.log_error(f"Error fetching attendance from device {self.device_id}: {str(e)}", 
                           "Biometric Device Error")
            raise e
        finally:
            if conn:
                conn.enable_device()
                conn.disconnect()

    def process_attendance_logs(self, logs):
        """Process attendance logs and create Employee Checkin entries"""
        settings = frappe.get_single("Biometric Settings")
        
        for log in logs:
            try:
                # Determine punch direction
                punch_direction = self.punch_direction
                if punch_direction == 'AUTO':
                    if log['punch'] in [0, 4]:  # Assuming these are IN punches
                        punch_direction = 'IN'
                    elif log['punch'] in [1, 5]:  # Assuming these are OUT punches
                        punch_direction = 'OUT'
                    else:
                        punch_direction = None
                
                # Create Employee Checkin
                # checkin = frappe.get_doc({
                #     "doctype": "Employee Checkin",
                #     "employee_field_value": log['user_id'],
                #     "time": log['timestamp'],
                #     "device_id": self.device_id,
                #     "log_type": punch_direction
                # })
                add_log_based_on_employee_field(
                    employee_field_value= log['user_id'],
                    timestamp= log['timestamp'],
                    device_id = self.device_id,
                    log_type= punch_direction
                )
                
                # checkin.insert()
                
            except Exception as e:
                error_msg = str(e)
                
                # Handle allowed exceptions based on settings
                if (("No Employee found" in error_msg and settings.ignore_employee_not_found) or
                    ("Inactive Employee" in error_msg and settings.ignore_inactive_employee) or
                    ("Duplicate Employee Checkin" in error_msg and settings.ignore_duplicate_checkin)):
                    continue
                    
                frappe.log_error(
                    f"Error processing attendance log for device {self.device_id}, user {log['user_id']}: {error_msg}",
                    "Biometric Attendance Processing Error"
                ) 