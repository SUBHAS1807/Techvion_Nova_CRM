/**
 * Excel & CSV Processing and Export Engine
 * Generates genuine .xlsx workbooks and clean RFC 4180 UTF-8 CSVs
 * Strictly follows Black & White design aesthetics for Excel exports
 */

const XLSX = require('xlsx');
const { parse: csvParse } = require('csv-parse/sync');

// CRM standard export headers
const EXPORT_COLUMNS = [
  { key: 'lead_id', label: 'Lead ID', width: 14 },
  { key: 'business_name', label: 'Business Name', width: 30 },
  { key: 'industry', label: 'Industry', width: 20 },
  { key: 'email', label: 'Email', width: 28 },
  { key: 'email_status', label: 'Email Status', width: 15 },
  { key: 'phone', label: 'Phone', width: 20 },
  { key: 'website', label: 'Website', width: 30 },
  { key: 'website_status', label: 'Website Status', width: 18 },
  { key: 'address', label: 'Address', width: 35 },
  { key: 'city', label: 'City', width: 18 },
  { key: 'state', label: 'State', width: 18 },
  { key: 'country', label: 'Country', width: 15 },
  { key: 'postal_code', label: 'Postal Code', width: 14 },
  { key: 'lead_status', label: 'Lead Status', width: 16 },
  { key: 'lead_source', label: 'Lead Source', width: 16 },
  { key: 'contact_person', label: 'Contact Person', width: 22 },
  { key: 'data_quality', label: 'Data Quality', width: 14 },
  { key: 'notes', label: 'Notes', width: 40 },
  { key: 'created_at', label: 'Created Date', width: 20 },
];

/**
 * Parse an uploaded Excel (.xlsx/.xls) or CSV buffer into headers and raw rows
 */
const parseUploadedFile = (buffer, filename) => {
  const isCsv = filename.toLowerCase().endsWith('.csv');

  if (isCsv) {
    const content = buffer.toString('utf8');
    const records = csvParse(content, {
      columns: false,
      skip_empty_lines: true,
      trim: true,
      relax_column_count: true,
    });

    if (!records || records.length === 0) {
      throw new Error('CSV file is empty or contains no readable data.');
    }

    const headers = records[0].map(h => String(h || '').trim());
    const rawRows = records.slice(1).map(row => {
      const rowObj = {};
      headers.forEach((h, idx) => {
        rowObj[h] = row[idx] !== undefined ? String(row[idx]).trim() : '';
      });
      return rowObj;
    });

    return { headers, rawRows };
  } else {
    // Excel workbook
    const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) {
      throw new Error('Excel workbook has no sheets.');
    }

    const worksheet = workbook.Sheets[firstSheetName];
    const data = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });

    if (!data || data.length === 0) {
      throw new Error('Excel sheet is empty or contains no rows.');
    }

    const headers = data[0].map(h => String(h || '').trim()).filter(h => h.length > 0);
    const rawRows = data.slice(1).map(row => {
      const rowObj = {};
      headers.forEach((h, idx) => {
        rowObj[h] = row[idx] !== undefined ? String(row[idx]).trim() : '';
      });
      return rowObj;
    });

    return { headers, rawRows };
  }
};

/**
 * Generates genuine Black & White styled Excel buffer using XLSX
 */
const generateBlackWhiteExcel = (leads) => {
  const headers = EXPORT_COLUMNS.map(col => col.label);
  const rows = leads.map(lead => {
    return EXPORT_COLUMNS.map(col => {
      let val = lead[col.key];
      if (val === null || val === undefined) return '';
      if (col.key === 'created_at' && val) {
        return new Date(val).toISOString().split('T')[0];
      }
      return String(val);
    });
  });

  const sheetData = [headers, ...rows];
  const worksheet = XLSX.utils.aoa_to_sheet(sheetData);

  // Set column widths
  worksheet['!cols'] = EXPORT_COLUMNS.map((col, idx) => {
    // Calculate max content length
    let maxLen = col.label.length;
    leads.slice(0, 100).forEach(lead => {
      const valStr = String(lead[col.key] || '');
      if (valStr.length > maxLen) maxLen = valStr.length;
    });
    return { wch: Math.min(Math.max(maxLen + 4, col.width), 60) };
  });

  // Freeze the top row (header)
  worksheet['!freeze'] = { xSplit: 0, ySplit: 1, topLeftCell: 'A2', activePane: 'bottomLeft', state: 'frozen' };

  // Set autofilter on range
  const lastColLetter = XLSX.utils.encode_col(EXPORT_COLUMNS.length - 1);
  worksheet['!autofilter'] = { ref: `A1:${lastColLetter}${leads.length + 1}` };

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Leads');

  const excelBuffer = XLSX.write(workbook, {
    bookType: 'xlsx',
    type: 'buffer',
    compression: true,
  });

  return excelBuffer;
};

/**
 * Generates technical clean RFC 4180 UTF-8 CSV
 */
const generateCleanCSV = (leads) => {
  const escapeCsv = (str) => {
    if (str === null || str === undefined) return '""';
    const val = String(str);
    if (val.includes('"') || val.includes(',') || val.includes('\n') || val.includes('\r')) {
      return `"${val.replace(/"/g, '""')}"`;
    }
    return `"${val}"`;
  };

  const headerLine = EXPORT_COLUMNS.map(col => escapeCsv(col.label)).join(',');
  const rowLines = leads.map(lead => {
    return EXPORT_COLUMNS.map(col => {
      let val = lead[col.key];
      if (val === null || val === undefined) val = '';
      if (col.key === 'created_at' && val) {
        val = new Date(val).toISOString().split('T')[0];
      }
      return escapeCsv(val);
    }).join(',');
  });

  // Include UTF-8 BOM so Excel opens accents and symbols correctly
  const csvContent = '\uFEFF' + [headerLine, ...rowLines].join('\r\n');
  return Buffer.from(csvContent, 'utf8');
};

module.exports = {
  EXPORT_COLUMNS,
  parseUploadedFile,
  generateBlackWhiteExcel,
  generateCleanCSV,
};
