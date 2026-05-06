import ctypes
import sys

# Check if running as admin
is_admin = ctypes.windll.shell32.IsUserAnAdmin()
print('Running as admin: {}'.format(is_admin))

# Check process integrity
import win32api
import win32security

pid = 40028
hproc = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
if hproc:
    token = win32security.OpenProcessToken(hproc, win32con.TOKEN_QUERY)
    integrity = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
    print('Process integrity level: {}'.format(integrity))
    win32api.CloseHandle(hproc)
