
function WriteLog {
    Param ([string]$logFile, [string]$logString)

    $timeStamp = (Get-Date).toString("yyyy/MM/dd HH:mm:ss")
    $logMessage = "$timeStamp $logString"
    Write-Host $logMessage
    Add-content $logFile -value $logMessage
}

$mainConfig = @{
    logFile = "$home\logs\RSSH.log"
    expectedInterfaceAlias = "Wi-Fi"
    #expectedInterfaceAlias = "Ethernet"
    allowedIPv4Ranges = @(
        ('192.168.1.1', '192.168.1.254'),
        ('192.168.10.1', '192.168.10.254'),
        ('192.168.100.1', '192.168.100.254')
    )
    sshClient = @{
        strictHostKeyChecking = 'no'
        sshConnectionPort = 33892
        sshListenPort = 3389
        sshRemoteHost = '192.168.77.12'
        sshUserName = 'rdpbastion'
        tunnelRemoteIP = '127.0.0.1'
        tunnelRemotePort = 3389
        globalKnownHostsFile = '/dev/null'
        userKnownHostsFile = '/dev/null'
        ipQoS = 'af21'
        serverAliveInterval = 3
        tcpKeepAlive = 'yes'
    }
}

if (Get-Process ssh -ErrorAction SilentlyContinue) {
    $sshProcesses = (Get-CimInstance Win32_Process -Filter "name='ssh.exe'")
    $sshPortForwardString = (-join([string]$mainConfig['sshClient']['sshListenPort'], ':',
                                    [string]$mainConfig['sshClient']['tunnelRemoteIP'], ':', 
                                    [string]$mainConfig['sshClient']['tunnelRemotePort']))
    if ($sshProcesses -is [system.array]) {
        foreach ($process in $sshProcesses) {
            if ($null -ne $process.CommandLine -And $process.CommandLine.Contains($sshPortForwardString)) {
                WriteLog $mainConfig['logFile'] '[!] The another SSH process',
                                    $process.ProcessId, 'with same port forwarding option is already running'
                Exit 71
            }
        }
    } else {
        if ($null -ne $sshProcesses.CommandLine -And $sshProcesses.CommandLine.Contains($sshPortForwardString)) {
            WriteLog $mainConfig['logFile'] '[!] The another SSH process',
                                $sshProcesses.ProcessId, 'with same port forwarding option is already running'
            Exit 71
        }
    }
}

$interfaceIndex = (Get-NetConnectionProfile | Select-Object -ExpandProperty InterfaceIndex)
if (!$interfaceIndex) {
    WriteLog $mainConfig['logFile'] '[!] Operation System is offline, please connect to a network'
    Exit 67
} elseif ($interfaceIndex -is [system.array]) {
    WriteLog $mainConfig['logFile'] '[!] Operatoin System has multiple network connections'
}

$currentIPv4 = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $interfaceIndex | 
                    Where-Object {$_.InterfaceAlias -eq $mainConfig['expectedInterfaceAlias']} | Select-Object -ExpandProperty IPAddress)
                    
if (!$currentIPv4) {
    WriteLog $mainConfig['logFile'] '[!] Cannot find active IPv4 address for expected', $mainConfig['expectedInterfaceAlias'], 'network interface' 
    Exit 67
}

WriteLog $mainConfig['logFile'] '[+] Current active IPv4 address:', $currentIPv4

foreach ($range in $mainConfig['allowedIPv4Ranges']) {
    if (([version]$range[0]) -lt ([version]$currentIPv4) -and ([version]$currentIPv4) -lt ([version]$range[1])) {
        WriteLog $mainConfig['logFile'] '[+] Work within the allowed IPv4 subnet range:', $range[0], '-', $range[1]
        WriteLog $mainConfig['logFile'] "[+] Start SSH tunnel with port forwarding:`n`t", (-join([string]$mainConfig['sshClient']['tunnelRemoteIP'],
                                                ':', [string]$mainConfig['sshClient']['tunnelRemotePort'],
                                                ' <-> ', [string]$mainConfig['sshClient']['sshRemoteHost'],
                                                ':', [string]$mainConfig['sshClient']['sshListenPort']))

        if (Test-Path $home/.ssh/known_hosts) {
            Remove-Item -Force $home/.ssh/known_hosts
        }

        # ssh -p 33892 -R 3389:127.0.0.1:3389 -o StrictHostKeyChecking=no -o GlobalKnownHostsFile=/dev/null -o UserKnownHostsFile=/dev/null -o IPQoS=throughput -o ServerAliveInterval=3 -o TCPKeepAlive=yes rdpbastion@192.168.77.12
        Start-Process -WindowStyle hidden -FilePath "ssh.exe" -ArgumentList '-p', $mainConfig['sshClient']['sshConnectionPort'],
                                                '-R', (-join([string]$mainConfig['sshClient']['sshListenPort'], ':', 
                                                            [string]$mainConfig['sshClient']['tunnelRemoteIP'], ':', 
                                                            [string]$mainConfig['sshClient']['tunnelRemotePort'])),
                                                '-o', (-join('StrictHostKeyChecking', '=', $mainConfig['sshClient']['strictHostKeyChecking'])),
                                                '-o', (-join('GlobalKnownHostsFile', '=', $mainConfig['sshClient']['globalKnownHostsFile'])),
                                                '-o', (-join('UserKnownHostsFile', '=', $mainConfig['sshClient']['userKnownHostsFile'])),
                                                '-o', (-join('IPQos', '=', $mainConfig['sshClient']['ipQoS'])),
                                                '-o', (-join('ServerAliveInterval', '=', $mainConfig['sshClient']['serverAliveInterval'])),
                                                '-o', (-join('TCPKeepAlive', '=', $mainConfig['sshClient']['tcpKeepAlive'])),
                                                (-join($mainConfig['sshClient']['sshUserName'], '@', $mainConfig['sshClient']['sshRemoteHost']))
    }
}

