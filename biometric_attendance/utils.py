import frappe
from frappe import _
from datetime import datetime, timedelta
import os

def setup_biometric_sync():
    """Setup the background job for biometric sync"""
    if not frappe.db.exists('Scheduled Job Type', 'biometric_attendance_sync'):
        frappe.get_doc({
            'doctype': 'Scheduled Job Type',
            'method': 'biometric_attendance.utils.sync_biometric_attendance',
            'frequency': 'Cron',
            'cron_format': '*/15 * * * *',  # Run every 15 minutes
            'name': 'biometric_attendance_sync'
        }).insert()


@frappe.whitelist()
def sync_biometric_attendance():
    """Main function to sync attendance from all devices"""
    settings = frappe.get_single("Biometric Settings")
    
    if not settings.enabled:
        return
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(settings.logs_directory):
        os.makedirs(settings.logs_directory)
    
    # Get all active devices
    devices = frappe.get_all("Biometric Device", 
                            fields=["name", "device_id", "ip_address", "port", 
                                  "punch_direction", "clear_from_device_on_fetch"])
    
    for device_data in devices:
        try:
            device = frappe.get_doc("Biometric Device", device_data.name)
            
            # Get attendance logs from device
            logs = device.get_attendance_logs()
            
            if logs:
                # Filter logs if import_start_date is set
                if settings.import_start_date:
                    logs = [log for log in logs 
                           if log['timestamp'].date() >= settings.import_start_date]
                
                # Process the logs
                device.process_attendance_logs(logs)
                
                # Update shift sync timestamps
                update_shift_sync_timestamps(device)
                
        except Exception as e:
            frappe.log_error(
                f"Error syncing attendance for device {device_data.device_id}: {str(e)}",
                "Biometric Sync Error"
            )

def update_shift_sync_timestamps(device):
    """Update last sync timestamp for associated shift types"""
    now = datetime.now()
    
    for shift in device.shift_types:
        frappe.db.set_value('Shift Type', shift.shift_type, 
                           'last_sync_of_checkin', now)
    
    frappe.db.commit()


@frappe.whitelist()
def get_last_sync_status():
    """Get the last sync status for all devices"""
    devices = frappe.get_all("Biometric Device", 
                            fields=["device_id", "ip_address"])
    
    status = []
    for device in devices:
        # Get the last error log for this device
        last_error = frappe.get_all(
            "Error Log",
            filters={
                "method": ["like", f"%{device.device_id}%"]
            },
            fields=["creation", "error"],
            order_by="creation desc",
            limit=1
        )
        
        # Get the last successful sync from shift types
        shifts = frappe.db.sql("""
            SELECT MAX(st.last_sync_of_checkin) as last_sync
            FROM `tabShift Type` st
            INNER JOIN `tabBiometric Device Shift` bds ON bds.shift_type = st.name
            INNER JOIN `tabBiometric Device` bd ON bd.name = bds.parent
            WHERE bd.device_id = %s
        """, (device.device_id,), as_dict=1)
        
        status.append({
            "device_id": device.device_id,
            "ip_address": device.ip_address,
            "last_sync": shifts[0].last_sync if shifts and shifts[0].last_sync else None,
            "last_error": last_error[0] if last_error else None
        })
    
    return status 