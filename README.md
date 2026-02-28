This started as a collection of scripts to Bridge Orcaslicer with Elegoo Centauri Carbon.

But as I added more and more stuff, I eventually rewrote the whole thing. What was once a single daemon.py file. Has turned into something much more.

Not everything is perfect. It works mostly for my own setup. BUT this can work for anyone else as long as the config file is filled properly.

I am also attempting to make this work within a docker container to allow for a persistent "always on" type mode. That is more of a WIP, so default, we will be running this more as a one and done script whenever you click on "Print" in Orcaslicer.

To accomplish this, included is another file "copy_to_watch.py". ATM, this file needs to be edited to your needs. But the purpose of this file is to act as a intermediatory between the daemon and Orca for the purpose of exporting / saving the GCODE to a watch folder of your choice that the daemon can read. Because, while print sends the GCODE to the printer, we don't have the file. YET!

(as I have been looking throught the sdcp api, there are ways I can list / delete file on the printer. I may work out a way to perhpas copy the currently printing GCODE across to a "watch" folder, to then extract the information required for the daemon. EG filament color, gram usage estimate.
Perhaps a work flow, instead of the watch_folder, could be:
	1. Detect Print.
	2. Copy GCODE / Read GCODE of current print.
	3. Extract info from GCODE to variables.
	4. When print is complete, instead of deleting file from watch_folder, we can instead have the option to delete it from the printer.
	
This would remove all need of a copy_to_watch.py at all, it would also remove the need of post processing in orca as well. Which would make setup easier.) Forgive my rambling, my brainstorming is just typing my thoughts. This doesn't belong in a README, so I will transfer this into issues and features when I have time.

Why not include it within the daemon? I would like to, and to be honest, I am not sure why it isn't. There was some reason I had to have it seperate. Ideally I'd like it to be all in one. Perhaps, it was because I was trying to make this universal between network mounts and stuff.

Now, why have I made this?


I like the idea of having an inventory of the spool I have and what I have left, even if its just a decent estimate. 
Unfortunately the Centauri Carbon isn't able to integrate with spoolman directly, and the newer versions of orcaslicer has no way to link with spoolman either.



Sure, we could input all the data manually if we wanted. But I like when things happen automatically!





You can run it in 2 ways:



1. Always Running Mode:



&nbsp;	you can run this script in the background as a service on Linux or windows by calling either run.bat or run.sh.

&nbsp;	This will allow it to be monitoring the defined watch folder for new gcode entries, and then when a print job matching that gcode is started, it will subtract the filament used

&nbsp;	to a matching spool in spoolman.



2\. One Time Mode:



&nbsp;	If you'd prefer, this can be run once when you click print in orcaslicer. Only modification required is to add a post-process script entry to copy\_to\_watch.py where you should save

&nbsp;	locally. EG in my orcaslicer dir, I created a folder "Scripts" and put the copy\_to\_watch.py file there. 

&nbsp;	This will instead run the daemon when you click print and will self close the daemon when the print is finished. You can see when the filament has been subtracted via the console,

&nbsp;	so if you choose, you can close the terminal window when you see that.

	When exporting g-code, it will also run the daemon. So if you aren't planning on printing, just close the daemon.







\*/ Installation /\*



Just extract all files to a place you want to run the daemon from. And then place the copy\_to\_watch.py file into a location of your choice that orcaslicer can access.

Then you must setup post-process scripts within orcaslicer, pointing to this python file.



\*\*\*NOTE\*\*\* You will need to have python installed to run the initial script! But the daemon will install its required packages into a venv via the requirements.txt file included.





You must open config_example.json and enter all fields to ensure that the daemon can access all required parameters. It must be then saved as config.json for the daemon to work.



&nbsp;	1. "sdcp\_ws\_url": "ws://<YOUR PRINTER IP HERE>:3030/websocket?command=subscribe"

&nbsp;		

&nbsp;		This is the access point to the printer for the daemon, it will subscribe and listen to Topic statuses. EG Printing / Idle / Paused.

&nbsp;		I have only tried this with OPEN CENTAURI and not stock firmware.



&nbsp;	2. "watch\_folder": "<THIS CAN BE ANY FOLDER EVEN ON A NETWORK SHARE THAT ORCASLICER AND THE DAEMON CAN ACCESS>"



&nbsp;		This is the folder that will contain a copy of the GCODE that is sent to the printer. This is so the daemon can open and parse for filament information.

&nbsp;		

&nbsp;	3. "spoolman\_local\_url": "http://localhost:7912" 



&nbsp;		Rare that you would need to change this as it is a fall back point if it is unreachable at spoolman\_url. If both are unreachable, than spoolman isn't setup currently.



&nbsp;	4. "spoolman\_url": "http://<SPOOLMAN\_IP>:7912"

&nbsp;		

&nbsp;		IP to spoolman service / container.



&nbsp;	5. "delete\_after\_print": true



&nbsp;		Great for 1 time prints. Work flow is Click Print in Orca --> File is created in Watch Folder --> Metadata is parsed --> Printer starts printing matching file -->

&nbsp;		daemon uses filament info to call spoolman api and subtract filament from spool --> deletes gcode file.



&nbsp;		But if you set this to false, the gcode will stay in the folder. This can be useful if you run the script on always on and you have a file on the printer you print often	

&nbsp;		from the printers interface. Then this should still work and subtract the filament as it will still match the gcode files.



&nbsp;	6. "always\_running": true



&nbsp;		keeps the websocket alive continues to watch the folder for new gcodes to parse. This is great when you want it to just run in the background and just send print jobs when  			needed. I am even considering creating a companion docker container that you could spin up in a stack with spoolman so it just runs in its own.



&nbsp;		But you can also have this as false if you'd prefer to spin it up on demand. 



&nbsp;	7. "hide\_one\_time\_mode\_terminal": false



&nbsp;		This is to work with always running set to true. When this is true, when you print the file it will hide the terminal and run it in the background. Only set this 

&nbsp;		if you are determined to declutter you PC. I prefer to have the console shown as then I know for sure the process closes / ends when the print job is finished

&nbsp;		and if not, I can just close the terminal window.







\*/ Additional Setup /\*



You need to name your filament in Orcaslicer a certain way for this to work. 



<manufacturer> - <type> - <color> == ELEGOO - PLA - Black



as long as you name the filament preset like this, then the parser can identify and then match your spools in spoolman. If you create any of your own custom spools, you need to copy how all the external filaments are named to keep consistency.



I decided on this format so that you can expand your spool inventory across many vendors, types and colors. And so that the daemon won't subtract the wrong filament from the wrong spool.







\*/ Troubleshooting /\*



If you are going to utilize the hide\_one\_time\_terminal, you should know this line in powershell to help you identify id's to stop if for some reason something is stuck.



```

Get-CimInstance Win32\_Process -Filter "Name = 'python.exe'" | Select-Object ProcessId, CommandLine

```



This will display the process running and their script names. EG /path/to/daemon.py. If needed, you can force close the daemon by:



```
Stop-Process -Id <ID>

```


