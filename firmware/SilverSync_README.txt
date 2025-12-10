SilverSync README for SiliconLabs Bluetooth AoA Location Finding
Gecko SDK v4.4.6


HOW TO USE
-----------------------------------------------------------------------------------------------------
Antenna Array will be referred to as AA
Antenna Array + WSTk (Pro Kit Mainboard) in combination will be referred to as AAW


Setting Up Antenna Array + WSTK within Simplicity Studio:
*********************************************************
1. Go to Launcher
2. Click on Wireless Pro Kit Mainboard
	Note: if more than AAW is connected to your device. Ensure you select the device 
	that you want to configure.
3. Set Debug mode to OUT
4. In Device Hardware > Boards, type "antenna array" and select the appropriate antenna array board
	(Our boards are the BRD4292A RevA03)
	Once the board is selected the BRD4002A (Wireless Pro Kit Mainboard/WSTK) should automatically
	be detected as well.
5. Back in the main launcher window set the Preferred SDK to "Gecko SDK Suite v4.4.6"
6. Under Example Projects & Demos search "aoa" or scroll until you find the 
   "Bluetooth AoA - NCP locator" demo program. Click Run on this program.
7. The AAW may not have a bootloader by default. To ensure the correct bootloader is installed 
   click Tools (top left of window) > Flash Programmer. Then Select the AA you just flashed the
   demo program to.
8. Select the file located at the location specified in "Path to Antenna Array Bootloader" above.
	Note: the file will not show up until you select the file type "*.s37"
9. Click program to flash the selected bootloader


Setting IP Address on AAW:
**************************
1. Connect AAW to computer via micro-usb (JLINK) and Ethernet
	Note: micro-usb must be capable of data transfer to program board
2. Open SimplicityCommander
3. In the dropdown menu at the top left of the display, select the AAW you wish to program
Optional. Assign Nickname to the device for easier recognition in the future
4. Click Edit under Network Information
5. Uncheck DCHP
6. Set IP Address using the following convention:
	192.168.137.1{AAW_num}
	where {AAW_num} is replaced by the number you associate with the AAW you are programming

	example: 192.168.137.13 for AAW with Nickname "AntennaArray3"

7. Set Gateway to the IP Address of the device running the AoA Host Locator program
	(For ease of use, utilize the IP Address 192.168.137.1 for the host)

CHANGEME: Add CLI commands to change IP Address and Default Gateway if GUI does not work


Using the AoA Host Locator Demo Program:
****************************************
1. Install all dependencies
2. Open MSYS2 MINGW64 and navigate to path in "AoA Host Locator Path MSYS MINGW64" above
3. Enter the command: "make"
4. Open Bash terminal and navigate back to path in "AoA Host Locator Path MSYS MINGW64"
5. Run using Serial or Ethernet

	Serial: enter the command "./exe/bt_aoa_host_locator.exe -u COM{num}" 
		where {num} is replaced by the comport that the AAW
	
		example: "./exe/bt_aoa_host_locator.exe -u COM7"

	Ethernet: enter the command "./exe/bt_aoa_host_locator.exe -t {ip_addr_wstk}"
		where {ip_addr_wstk} is replaced by the ip address assigned to the WSTK
		(this can be found either by going using the app SimplicityCommander
		or by looking at the screen on the WSTK if an Ethernet connection
		has been established)

		example: "./exe/bt_aoa_host_locator.exe -t 192.168.137.11"

	IF ERROR: ".../bt_aoa_host_locator/exe/bt_aoa_host_locator.exe: error while loading
		shared libraries: mosquitto.dll: cannot open shared object file: No such file 
		or directory"

		Find the path to mosquitto.dll then link it to the current path by using this 
		command within Bash: export PATH="/c/{your_path}/mosquitto:$PATH"
		where {your_path} is replaced by the path to the directory containing
		mosquitto.dll

		example: export PATH="/c/Program Files/mosquitto:$PATH"

6. Open MQTT Explorer and set the parameters as such:
	Name: mqtt.eclipse.org
	Host: Localhost
	Port: 1883
	(select save to save these parameters for future use)
7. Click connect



If NCP host program keeps connecting and disconnecting from MQTT broker
----------------------------------------------------------------------
In Bash enter the following commands:
sudo systemctl stop mosquitto
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto








PIC Antenna Positions
-----------------------------------------------------------------------

            PIC Map

     **********************                                 
     * 4            1     *
     *                    |  entrance               
     *                    *                          X+ <-----
     *                    *                                   |
     *                 ****                                   |
     *                 *  "                                   V  Y+ 
exit |                 *  " computer room
     * 3            2  *  "
     *******************"""  


Coordinates Based on Ceiling Tiles (24 in/tile)

AA1: (0 in, 0 in)      ---       (0.000 m, 0.000 m)
AA2: (0 in, 240 in)    ---       (0.000 m, 6.096 m)
AA3: (360 in, 240 in)  ---       (9.144 m, 6.096 m)
AA4: (360 in, 0 in)    ---       (9.144 m, 0.000 m)

Elevation (Z-coord) (88 in) ---  (2.235 m)




Steps to Increase Positioning Precision (filtering)
----------------------------------------------------------------------
1. adjust cte advertising length to 100 ms

	#define SL_GATT_SERVICE_CTE_SILABS_ADV_INTERVAL   160

2. adjust estimation interval within positioning json to match cte adv length

	"estimationIntervalSec" : 0.1

3. maximize position smoothing weight in positioning json

	"locationFilteringWeight": 0.4

4. enable angle filterig for each location in positioning json

	"angleFiltering": True

5. set validation to HIGH

	"validationModeLocation": "SL_RTL_LOC_MEASUREMENT_VALIDATION_HIGH"

6. set location estimation mode to 2D

	"estimationModeLocation": "SL_RTL_LOC_ESTIMATION_MODE_TWO_DIM_HIGH_ACCURACY"




Antenna Array IDs
----------------------------------------------------------------------
AA1: ble-pd-0C4314F03448
AA2: ble-pd-0C4314F03444
AA3: ble-pd-50325FAB8F57
AA4: ble-pd-0C4314F03468


Pathing
----------------------------------------------------------------------
AoA Host Locator Path MSYS MINGW64: /c/Users/willi/SimplicityStudio/SDKs/app/bluetooth/example_host/bt_aoa_host_locator

within this dir, enter: make

to run AoA Host Locator serial:
./exe/bt_aoa_host_locator.exe -u COM{num}

to run AoA Host Locator ethernet:
./exe/bt_aoa_host_locator.exe -t {ip_addr_wstk}

	if get a cannot find mosquitt.dll error:
	export PATH="/c/Program Files/mosquitto:$PATH"

to run Host Positioning:
./exe/bt_host_positioning.exe -c ./config/positioning_config.json -m localhost:1883

	get AAW id's from the MQTT server, not from SimplicityCommander


Path to Asset Tag Bootloader:
C:\SiliconLabs\SimplicityStudio\v5\offline\com.silabs.sdk.stack.super_4.4.6\platform\bootloader\demos\bootloader-apploader\bootloader-apploader-brd4184a.s37

Path to Asset Tag Example Program:
C:\SiliconLabs\SimplicityStudio\v5\offline\com.silabs.sdk.stack.super_4.4.6\app\bluetooth\demos\bt_aoa_soc_asset_tag\bt_aoa_soc_asset_tag-brd4184a.s37

Path to Antenna Array Bootloader:
C:\SiliconLabs\SimplicityStudio\v5\offline\com.silabs.sdk.stack.super_4.4.6\app\bluetooth\demos\bt_aoa_ncp_locator\bt_aoa_ncp_locator-brd4191a.s37
