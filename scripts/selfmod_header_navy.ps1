$ErrorActionPreference = 'Stop'

$base = 'https://nesako-production.up.railway.app'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# 1) Login to obtain session cookie
$loginBody = @{ username='nesako'; password='nesako2024' }
Invoke-WebRequest -Uri ($base + '/login/') -Method POST -Body $loginBody -WebSession $session | Out-Null

# 2) Build instruction JSON
$instruction = @'
SAMOPROMENA: U templates/index.html postavi .header background na #0a1a2b (teget) i dodaj inline style background:#0a1a2b na div.header. Ne menjaj #ffffff tekst niti layout. Zatim uradi: git add templates/index.html; git commit -m feat-ui-header-navy-0a1a2b; git push origin main. Vrati kratak diff (broj izmena) i potvrdu push-a.
'@
$payload = @{ instruction = $instruction; conversation_history = @(); allow_self_modification = $true; auto_execute = $true; confirmation_type = 'plan_autoapprove' } | ConvertTo-Json -Depth 6

# 3) Trigger self-mod
$response = Invoke-RestMethod -Uri ($base + '/api/chat/') -Method POST -ContentType 'application/json; charset=utf-8' -Body $payload -WebSession $session
$response | ConvertTo-Json -Depth 12 | Out-Host

# 4) Poll if executing
if ($response -and $response.status -eq 'executing' -and $response.task_id) {
  $task = $response.task_id
  for ($i=0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 3
    $poll = @{ task_id = $task; instruction=''; conversation_history=@() } | ConvertTo-Json -Depth 5
    $r2 = Invoke-RestMethod -Uri ($base + '/api/chat/') -Method POST -ContentType 'application/json; charset=utf-8' -Body $poll -WebSession $session
    $r2 | ConvertTo-Json -Depth 12 | Out-Host
    if ($r2.status -in @('completed','success')) { break }
  }
}
