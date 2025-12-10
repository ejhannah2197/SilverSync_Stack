#!/bin/bash

echo -e "\n"
echo -e "         SilverSync Position Finding Program\n"


/home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_host_positioning/exe/bt_host_positioning -c /home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_host_positioning/config/positioning_config.json -m localhost:1883 &
if [ $? -ne 0 ]; then
    echo -e "\nFATAL ERROR: bt_host_positioning failed to run. Check if ./config/positioning_config.json exists and is readable."
    exit 1
fi


read