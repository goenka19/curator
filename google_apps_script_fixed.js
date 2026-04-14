var SECRET_KEY = "curator_ig_queue_2026";

function doPost(e) {
  return handleRequest(e);
}

function doGet(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  try {
    var data;
    
    // Handle POST requests (from Python backend)
    if (e.postData && e.postData.contents) {
      data = JSON.parse(e.postData.contents);
    }
    // Handle GET requests with URL params (from iOS Shortcuts)
    else if (e.parameter) {
      data = e.parameter;
    }
    else {
      return response({"status": "error", "message": "No data received"});
    }
    
    // Verify secret
    if (data.secret !== SECRET_KEY) {
      return response({"status": "error", "message": "Unauthorized - secret mismatch"});
    }
    
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Queue');
    
    // ACTION: Add to queue (explicit action OR implicit from iOS Shortcut)
    // FIX #1: Handle iOS Shortcut GET requests (no action field)
    if (data.action === 'add' || (data.url && !data.action)) {
      var url = data.url;
      var cleanedUrl = url.split('?')[0];
      if (!cleanedUrl.endsWith('/')) cleanedUrl += '/';
      // FIX #2: Store retry_count as number 0, not string "0"
      sheet.appendRow([new Date(), url, cleanedUrl, 'pending', 0, '', '', '']);
      return response({"status": "success", "message": "Added to queue"});
    }
    
    // ACTION: Get pending items (for Python backend)
    if (data.action === 'get_pending' || !data.action) {
      var rows = sheet.getDataRange().getValues();
      var pending = [];
      for (var i = 1; i < rows.length; i++) {
        // FIX #3: Parse values properly to handle type issues
        var status = String(rows[i][3] || '').trim();
        var retryCount = parseInt(rows[i][4]) || 0;
        
        if (status === 'pending' && retryCount < 2) {
          pending.push({
            rowIndex: i + 1,
            url: rows[i][1],
            cleaned_url: rows[i][2],
            retry_count: retryCount  // Return as number
          });
        }
      }
      return response(pending);
    }
    
    // ACTION: Update row
    if (data.action === 'update') {
      var rowIndex = parseInt(data.rowIndex);
      if (data.status) sheet.getRange(rowIndex, 4).setValue(data.status);
      if (data.retry_count !== undefined) sheet.getRange(rowIndex, 5).setValue(parseInt(data.retry_count));
      if (data.processed_at) sheet.getRange(rowIndex, 6).setValue(data.processed_at);
      if (data.error_message) sheet.getRange(rowIndex, 7).setValue(data.error_message);
      if (data.db_id) sheet.getRange(rowIndex, 8).setValue(data.db_id);
      return response({"status": "success"});
    }
    
    // ACTION: Cleanup old rows
    if (data.action === 'cleanup') {
      var rows = sheet.getDataRange().getValues();
      var cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - 7);
      for (var i = rows.length; i > 1; i--) {
        var status = String(rows[i-1][3] || '').trim();
        var pAt = new Date(rows[i-1][5]);
        if (status === 'processed' && pAt < cutoff) {
          sheet.deleteRow(i);
        }
      }
      return response({"status": "success"});
    }
    
    return response({"status": "error", "message": "Unknown action: " + data.action});
    
  } catch(error) {
    return response({"status": "error", "message": error.toString()});
  }
}

function response(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
