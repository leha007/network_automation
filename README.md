# network_automation
Automate simple tasks for network device configuration

Script is controlled via config.json file and it's execution depends on it.

Notes:
1. If specific device doesn't have local cmd then global cmd will be used.
2. Secret is a password that is used for switching to enabled mode if needed, if user already privileged leave empty.
3. Commands will be executed in the same order as they added in config.json file.

Installation:
1. Install python 3.7
2. Run #pip install -r requirements.txt

Usage:
3. Edit config.json file according to your environment
4. Run script #python app.py