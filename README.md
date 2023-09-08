# bunkermessungai.local
this is the local cam repo for bunkermessungai.de


# >Install
#### *Linux setup* <br>

    sudo wget https://raw.githubusercontent.com/Erfinden/bunkermessungai.local/main/install.sh -O /usr/local/install.sh && sudo bash /usr/local/install.sh

#### *Windows setup* <br><br> | replace the USERPROFILE in the command with your username<br>| only via ip and not "bunkermessungai.local"<br>

    powershell -command "(New-Object Net.WebClient).DownloadFile('https://raw.githubusercontent.com/Erfinden/bunkermessungai.local/main/install.bat', '$env:USERPROFILE\Downloads\install.bat') ; Start-Process -Wait -FilePath 'C:\Windows\System32\cmd.exe' -ArgumentList '/C $env:USERPROFILE\Downloads\install.bat' ; schtasks /create /tn 'RunCamScript' /tr 'python $env:USERPROFILE\Downloads\cam.py' /sc onstart /ru 'System'"
