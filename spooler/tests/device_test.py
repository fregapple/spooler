from devices.airpurifier import AirPurifier

d = AirPurifier(
    dev_id="bffc5f3cf2ed8af39bcrgg",
    address="Auto",
    local_key="VRCJ$E5|EG[o-_7B",
    version=3.3,
)

print(d.status())
