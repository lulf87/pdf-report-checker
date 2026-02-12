import type { VerificationResult, InspectionItemCheckResult } from '../types';

// Export to Excel (CSV format)
export function exportToExcel(result: VerificationResult): void {
  const headers = [
    '字段名称',
    '表格值',
    'OCR识别值',
    '状态',
    '置信度',
    '页码',
    '表格行',
    '表格列',
  ];

  const rows = result.fields.map((field) => [
    field.fieldName,
    field.tableValue || '',
    field.ocrValue || '',
    getStatusText(field.status),
    `${(field.confidence * 100).toFixed(1)}%`,
    field.pageNumber,
    field.tableRow || '',
    field.tableCol || '',
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row
        .map((cell) => {
          const cellStr = String(cell);
          if (cellStr.includes(',') || cellStr.includes('"')) {
            return `"${cellStr.replace(/"/g, '""')}"`;
          }
          return cellStr;
        })
        .join(',')
    ),
  ].join('\n');

  const blob = new Blob(['\ufeff' + csvContent], {
    type: 'text/csv;charset=utf-8;',
  });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `核对报告_${result.fileName}_${formatDate(result.completedAt)}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// Export to PDF (HTML format for printing)
export function exportToPDF(result: VerificationResult): void {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('请允许弹出窗口以导出PDF');
    return;
  }

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>核对报告 - ${result.fileName}</title>
      <style>
        @page { size: A4; margin: 20mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
          font-size: 12pt;
          line-height: 1.6;
          color: #1E293B;
          padding: 20px;
        }
        .header {
          text-align: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 2px solid #3B82F6;
        }
        .header h1 {
          font-size: 24pt;
          color: #3B82F6;
          margin-bottom: 10px;
        }
        .header .meta {
          color: #64748B;
          font-size: 10pt;
        }
        .stats {
          display: flex;
          justify-content: space-around;
          margin-bottom: 30px;
          padding: 20px;
          background: #F8FAFC;
          border-radius: 8px;
        }
        .stat-item {
          text-align: center;
        }
        .stat-value {
          font-size: 28pt;
          font-weight: bold;
          color: #3B82F6;
        }
        .stat-label {
          font-size: 10pt;
          color: #64748B;
          margin-top: 5px;
        }
        .section {
          margin-bottom: 30px;
        }
        .section h2 {
          font-size: 14pt;
          color: #1E293B;
          margin-bottom: 15px;
          padding-bottom: 8px;
          border-bottom: 1px solid #E2E8F0;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 10pt;
        }
        th, td {
          padding: 10px 8px;
          text-align: left;
          border-bottom: 1px solid #E2E8F0;
        }
        th {
          background: #F1F5F9;
          font-weight: 600;
          color: #475569;
        }
        .status-matched { color: #10B981; font-weight: 600; }
        .status-mismatched { color: #EF4444; font-weight: 600; }
        .status-missing { color: #F59E0B; font-weight: 600; }
        .status-extra { color: #6B7280; font-weight: 600; }
        .summary {
          background: #EFF6FF;
          padding: 15px;
          border-radius: 8px;
          border-left: 4px solid #3B82F6;
        }
        .footer {
          margin-top: 40px;
          padding-top: 20px;
          border-top: 1px solid #E2E8F0;
          text-align: center;
          font-size: 9pt;
          color: #94A3B8;
        }
        @media print {
          .no-print { display: none; }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>报告核对结果</h1>
        <div class="meta">
          <p>文件名：${result.fileName}</p>
          <p>核对时间：${formatDateTime(result.completedAt)}</p>
          <p>报告ID：${result.id}</p>
        </div>
      </div>

      <div class="stats">
        <div class="stat-item">
          <div class="stat-value">${result.stats.totalFields}</div>
          <div class="stat-label">总字段数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #10B981;">${result.stats.matched}</div>
          <div class="stat-label">一致</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #EF4444;">${result.stats.mismatched}</div>
          <div class="stat-label">不一致</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" style="color: #F59E0B;">${result.stats.missing}</div>
          <div class="stat-label">缺失</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${(result.stats.confidence * 100).toFixed(1)}%</div>
          <div class="stat-label">整体置信度</div>
        </div>
      </div>

      <div class="section">
        <h2>详细核对结果</h2>
        <table>
          <thead>
            <tr>
              <th>字段名称</th>
              <th>表格值</th>
              <th>OCR识别值</th>
              <th>状态</th>
              <th>置信度</th>
              <th>位置</th>
            </tr>
          </thead>
          <tbody>
            ${result.fields
              .map(
                (field) => `
              <tr>
                <td>${field.fieldName}</td>
                <td>${field.tableValue || '-'}</td>
                <td>${field.ocrValue || '-'}</td>
                <td class="status-${field.status}">${getStatusText(
                  field.status
                )}</td>
                <td>${(field.confidence * 100).toFixed(1)}%</td>
                <td>第${field.pageNumber}页${
                  field.tableRow ? ` / 第${field.tableRow}行` : ''
                }</td>
              </tr>
            `
              )
              .join('')}
          </tbody>
        </table>
      </div>

      <div class="summary">
        <strong>核对总结：</strong>
        本次核对共检测 ${result.stats.totalFields} 个字段，
        其中 ${result.stats.matched} 个字段完全一致，
        ${result.stats.mismatched} 个字段存在差异，
        ${result.stats.missing} 个字段缺失。
        整体置信度为 ${(result.stats.confidence * 100).toFixed(1)}%。
      </div>

      <div class="footer">
        <p>由报告核对工具自动生成</p>
        <p>生成时间：${formatDateTime(new Date().toISOString())}</p>
      </div>

      <div class="no-print" style="text-align: center; margin-top: 30px;">
        <button onclick="window.print()" style="
          padding: 12px 30px;
          font-size: 14pt;
          background: #3B82F6;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        ">打印 / 保存为PDF</button>
      </div>
    </body>
    </html>
  `;

  printWindow.document.write(html);
  printWindow.document.close();
}

// Helper functions
function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    matched: '一致',
    mismatched: '不一致',
    missing: '缺失',
    extra: '额外',
  };
  return statusMap[status] || status;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toISOString().split('T')[0];
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Export inspection item check to Excel (CSV format)
export function exportInspectionItemsToExcel(
  result: InspectionItemCheckResult,
  fileName: string
): void {
  const headers = [
    '序号',
    '检验项目',
    '标准条款',
    '标准要求',
    '检验结果',
    '单项结论(实际)',
    '单项结论(期望)',
    '核对状态',
    '备注',
  ];

  const rows: string[][] = [];

  result.item_checks.forEach((item) => {
    item.clauses.forEach((clause) => {
      clause.requirements.forEach((req) => {
        rows.push([
          item.item_number,
          item.item_name,
          clause.clause_number,
          req.requirement_text,
          req.inspection_result,
          clause.conclusion,
          clause.expected_conclusion,
          clause.is_conclusion_correct ? '正确' : '错误',
          req.remark,
        ]);
      });
    });
  });

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row
        .map((cell) => {
          const cellStr = String(cell || '');
          if (cellStr.includes(',') || cellStr.includes('"') || cellStr.includes('\n')) {
            return `"${cellStr.replace(/"/g, '""')}"`;
          }
          return cellStr;
        })
        .join(',')
    ),
  ].join('\n');

  const blob = new Blob(['\ufeff' + csvContent], {
    type: 'text/csv;charset=utf-8;',
  });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `检验项目核对明细_${fileName}_${formatDate(new Date().toISOString())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}
