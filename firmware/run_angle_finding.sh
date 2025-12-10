#!/bin/bash

echo -e "\n"
echo -e "         SilverSync Angle Finding Program\n"

echo -e "____________________Ping AntennaArray1____________________"
ping -c 4 192.168.137.11
if [ $? -ne 0 ]; then
    echo -e "\nFATAL ERROR: Failed to ping 192.168.137.11"
    exit 1
fi

echo -e "\n"
echo -e "____________________Ping AntennaArray2____________________"
ping -c 4 192.168.137.12
if [ $? -ne 0 ]; then
    echo -e "\nFATAL ERROR: Failed to ping 192.168.137.12"
    exit 1
fi

echo -e "\n"
echo -e "____________________Ping AntennaArray3____________________"
ping -c 4 192.168.137.13
if [ $? -ne 0 ]; then
    echo -e "\nFATAL ERROR: Failed to ping 192.168.137.13"
    exit 1
fi

echo -e "\n"
echo -e "____________________Ping AntennaArray4____________________"
ping -c 4 192.168.137.14
if [ $? -ne 0 ]; then
    echo -e "\nFATAL ERROR: Failed to ping 192.168.137.14"
    exit 1
fi

echo -e "\n"
echo -e "__________Starting SilverSync Angle Finding Program__________"
/home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_aoa_host_locator/exe/bt_aoa_host_locator -t 192.168.137.11 &
/home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_aoa_host_locator/exe/bt_aoa_host_locator -t 192.168.137.12 &
/home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_aoa_host_locator/exe/bt_aoa_host_locator -t 192.168.137.13 &
/home/wake-engr/Desktop/SimplicityStudio/SilabsSDK_for_Pi/SDKs/app/bluetooth/example_host/bt_aoa_host_locator/exe/bt_aoa_host_locator -t 192.168.137.14 &
wait

echo -e "\nPress ENTER to close program"
read
