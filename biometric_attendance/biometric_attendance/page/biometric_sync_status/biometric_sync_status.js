frappe.pages['biometric-sync-status'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Biometric Sync Status',
		single_column: true
	});

	// Add refresh button
	page.set_primary_action('Refresh', () => {
		refresh_status();
	});

	// Add manual sync button
	page.set_secondary_action('Sync Now', () => {
		debugger;
		frappe.call({
			method: 'biometric_attendance.utils.sync_biometric_attendance',
			callback: function(r) {
				frappe.show_alert({
					message: 'Sync initiated',
					indicator: 'green'
				});
				setTimeout(refresh_status, 5000);
			}
		});
	});

	// Create status table
	let status_wrapper = $('<div class="status-table"></div>').appendTo(page.body);
	
	function refresh_status() {
		frappe.call({
			method: 'biometric_attendance.utils.get_last_sync_status',
			callback: function(r) {
				if (r.message) {
					let html = '<table class="table table-bordered">';
					html += '<thead><tr><th>Device ID</th><th>IP Address</th><th>Last Sync</th><th>Last Error</th></tr></thead>';
					html += '<tbody>';
					
					r.message.forEach(function(device) {
						html += '<tr>';
						html += `<td>${device.device_id || ''}</td>`;
						html += `<td>${device.ip_address || ''}</td>`;
						html += `<td>${device.last_sync ? frappe.datetime.str_to_user(device.last_sync) : 'Never'}</td>`;
						html += `<td>${device.last_error ? 
							`<div class="error-msg" title="${device.last_error.error}">${
								frappe.datetime.str_to_user(device.last_error.creation)
							}</div>` : ''}</td>`;
						html += '</tr>';
					});
					
					html += '</tbody></table>';
					status_wrapper.html(html);
				}
			}
		});
	}

	// Initial load
	refresh_status();
} 