# **Spooler – OrcaSlicer → Spoolman → Centauri Carbon Bridge**

This is collection of scripts I have created to bridge orca slicer with spoolman and the centauri carbon 3d printer.

---

## **Reason**

I like the idea of having an inventory of the spool I have and what I have left, even if its just a decent estimate.  
Unfortunately the Centauri Carbon isn't able to integrate with spoolman directly, and the newer versions of orcaslicer has no way to link with spoolman either.

Sure, we could input all the data manually if we wanted. But I like when things happen automatically!

---

# **How to Run It**

You can run it in **2 ways**:

---

## **1. Always Running Mode**

You can run this script in the background as a service on Linux or Windows by calling either **run.bat** or **run.sh**.

This will allow it to monitor the defined watch folder for new gcode entries, and then when a print job matching that gcode is started, it will subtract the filament used to a matching spool in spoolman.

---

## **2. One Time Mode**

If you'd prefer, this can be run once when you click print in orcaslicer.  
Only modification required is to add a post‑process script entry to **copy_to_watch.py** where you should save locally.  
EG: in my orcaslicer dir, I created a folder "Scripts" and put the copy_to_watch.py file there.

This will instead run the daemon when you click print and will self‑close the daemon when the print is finished.  
You can see when the filament has been subtracted via the console, so if you choose, you can close the terminal window when you see that.

When exporting g-code, it will also run the daemon.  
So if you aren't planning on printing, just close the daemon.

---

# **Installation**

Just extract all files to a place you want to run the daemon from.  
Then place the **copy_to_watch.py** file into a location of your choice that orcaslicer can access.

Then you must setup post‑process scripts within orcaslicer, pointing to this python file.

**NOTE:** You will need to have python installed to run the initial script!  
But the daemon will install its required packages via the requirements.txt file included.

You must open **config.json** and enter all fields to ensure that the daemon can access all required parameters.

---

# **Configuration**

### **1. `sdcp_ws_url`**
```
ws://<YOUR PRINTER IP HERE>:3030/websocket?command=subscribe
```
This is the access point to the printer for the daemon.  
It will subscribe and listen to Topic statuses (Printing / Idle / Paused).  
I have only tried this with OPEN CENTAURI and not stock firmware.

---

### **2. `watch_folder`**
```
<THIS CAN BE ANY FOLDER EVEN ON A NETWORK SHARE THAT ORCASLICER AND THE DAEMON CAN ACCESS>
```
This is the folder that will contain a copy of the GCODE that is sent to the printer.  
This is so the daemon can open and parse for filament information.

---

### **3. `spoolman_local_url`**
```
http://localhost:7912
```
Rare that you would need to change this as it is a fallback point if it is unreachable at spoolman_url.  
If both are unreachable, then spoolman isn't setup currently.

---

### **4. `spoolman_url`**
```
http://<SPOOLMAN_IP>:7912
```
IP to spoolman service / container.

---

### **5. `delete_after_print`**
```
true / false
```
Great for 1‑time prints.  
Workflow is:  
Click Print in Orca → File is created in Watch Folder → Metadata is parsed → Printer starts printing matching file → daemon uses filament info to call spoolman API and subtract filament → deletes gcode file.

But if you set this to false, the gcode will stay in the folder.  
This can be useful if you run the script always‑on and you have a file on the printer you print often from the printer’s interface.  
Then this should still work and subtract the filament as it will still match the gcode files.

---

### **6. `always_running`**
```
true / false
```
Keeps the websocket alive and continues to watch the folder for new gcodes to parse.  
This is great when you want it to just run in the background and just send print jobs when needed.

I am even considering creating a companion docker container that you could spin up in a stack with spoolman so it just runs on its own.

But you can also have this as false if you'd prefer to spin it up on demand.

---

### **7. `hide_one_time_mode_terminal`**
```
true / false
```
This is to work with always_running set to true.  
When this is true, when you print the file it will hide the terminal and run it in the background.

Only set this if you are determined to declutter your PC.  
I prefer to have the console shown as then I know for sure the process closes / ends when the print job is finished, and if not, I can just close the terminal window.

---

# **Additional Setup**

You need to name your filament in Orcaslicer a certain way for this to work:

```
<manufacturer> - <type> - <color>
Example: ELEGOO - PLA - Black
```

As long as you name the filament preset like this, then the parser can identify and match your spools in spoolman.  
If you create any of your own custom spools, you need to copy how all the external filaments are named to keep consistency.

I decided on this format so that you can expand your spool inventory across many vendors, types and colors.  
And so that the daemon won't subtract the wrong filament from the wrong spool.

---

# **Troubleshooting**

If you are going to utilize the hide_one_time_terminal, you should know this line in powershell to help you identify IDs to stop if for some reason something is stuck:

```
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Select-Object ProcessId, CommandLine
```

This will display the process running and their script names.  
EG: /path/to/daemon.py.

If needed, you can force close the daemon by:

```
Stop-Process -Id <ID>
```
