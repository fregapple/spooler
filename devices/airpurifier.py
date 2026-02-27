import tinytuya

data = {
        "name": "the Smart Air\u2122 Viral Protect Night Glow",
        "id": "bffc5f3cf2ed8af39bcrgg",
        "key": "VRCJ$E5|EG[o-_7B",
        "mac": "50:8b:b9:2e:87:2c",
        "uuid": "d3d0784e29039bfe",
        "sn": "1001091080101F",
        "category": "kj",
        "product_name": "the Smart Air\u2122 Viral Protect Night Glow",
        "product_id": "yueiqf0rh2uqkzfv",
        "biz_type": 18,
        "model": "LAP168",
        "sub": False,
        "icon": "https://images.tuyaeu.com/smart/icon/ay157353776524912KIV/1679961469811e21edca4.jpg"
    }

# d = tinytuya.Device(
#     dev_id="bffc5f3cf2ed8af39bcrgg",
#     address="Auto",
#     local_key="VRCJ$E5|EG[o-_7B",
#     version=3.3
# )

RED = "0000"
ORANGE = "001e"
YELLOW = "003c"
LIME = "005a"
GREEN = "0078"
AQUA = "0096"
CYAN = "00b4"
SKYBLUE = "00d2"
BLUE = "00f0"
PURPLE = "010e"
MAGENTA = "012c"
PINK = "014a"

class AirPurifier(tinytuya.Device):
    """
    Air purifier device class.
    """
    DPS = 'dps'
    DPS_POWER = "1"  
    DPS_MODE = "3"  # manual, sleep
    DPS_FAN_SPEED = "4" # high, medium, low
    DPS_FILTER_LIFE = "5" #READ-ONLY %
    DPS_LED = "8" # True/False
    DPS_FILTER_TIME = "16" #READ-ONLY Days
    DPS_COUNTDOWN = "18" # Cancel \ 2h \ 4h \ 8h
    DPS_TEST4 = "19" # Unknown, always 0?
    DPS_COLOR = "102"

    def __init__(self, dev_id, address, local_key, version, log, model=None, always_on=False):
        super().__init__(dev_id=dev_id, address=address, local_key=local_key, version=version)
        self.log = log
        self.model = model
        self.always_on = always_on

    def get_power(self):
        return self.status().get(self.DPS).get(self.DPS_POWER)
    
    def sleep_mode_on(self):
        self.set_value(self.DPS_MODE, "sleep")

    def sleep_mode_off(self):
        self.set_value(self.DPS_MODE, "manual")

    def get_mode(self):
        return self.status().get(self.DPS).get(self.DPS_MODE)

    def set_fan_speed(self, speed):
        if speed not in ["high", "mid", "low"]:
            raise ValueError("Invalid fan speed. Use 'high', 'mid', or 'low'.")
        self.set_value(self.DPS_FAN_SPEED, speed)

    def get_fan_speed(self):
        return self.status().get(self.DPS).get(self.DPS_FAN_SPEED)

    def led_on(self):
        self.set_value(self.DPS_LED, True)
    
    def led_off(self):
        self.set_value(self.DPS_LED, False)
    
    def get_led(self):
        return self.status().get(self.DPS).get(self.DPS_LED)

    def check_filter_life(self):
        return self.status().get(self.DPS).get(self.DPS_FILTER_LIFE)
    
    def set_countdown(self, hours):
        if hours not in ['cancel', '2h', '4h', '8h']:
            raise ValueError("Invalid countdown time. Use 0 (cancel), 2, 4, or 8 hours.")
        self.set_value(self.DPS_COUNTDOWN, hours)

    def get_countdown(self):
        return self.status().get(self.DPS).get(self.DPS_COUNTDOWN)
    
    def get_filter_time(self):
        return self.status().get(self.DPS).get(self.DPS_FILTER_TIME)
    
    def get_led_color(self):
        return self.status().get(self.DPS).get(self.DPS_TEST5)
    
    def set_led_color(self, color, brightness, saturation):

        brightness = max(0, min(100, float(brightness)))

        b_value = round(brightness * 10)  

        saturation = max(0, min(100, float(saturation)))

        s_value = round(saturation * 10)  
    
        self.set_value(self.DPS_COLOR, f"{color}{b_value:04x}{s_value:04x}")

    def to_dict(self):
        return {
            "type": "airpurifier",
            "id": self.id,
            "ip": self.address,
            "key": self.local_key,
            "version": self.version,
            "model": self.model,
            "always_on": self.always_on
        }
    


# device = AirPurifier(dev_id="bffc5f3cf2ed8af39bcrgg", address="auto", local_key="VRCJ$E5|EG[o-_7B", version=3.3)
# print(device.get_fan_speed())

# if device.get_power():
#     print("[DEVICE] Purifier already on, setting to sleep mode")
#     device.sleep_mode_on()
#     pass
# else:
#     print("[DEVICE] Powering on Purifier")
#     device.turn_on()
#     device.sleep_mode_on()
# print(device.status())