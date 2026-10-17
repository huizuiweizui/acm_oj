param([string]$In, [string]$Docx, [string]$Pdf)
# 用 Word 更新目录与域，另存 docx 并导出 PDF
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($In)
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  $d.Fields.Update() | Out-Null
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  $d.SaveAs2($Docx, 16)
  $d.ExportAsFixedFormat($Pdf, 17)
  "pages: " + $d.ComputeStatistics(2)
  $d.Close(0)
} finally { $w.Quit() }
