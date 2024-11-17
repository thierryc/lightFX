#!/usr/bin/env python3
import sys
import json
import argparse
import re
import time
from lifxlan import LifxLAN, Light, WorkflowException
from pathlib import Path

CONFIG_FILE = "lifx_config.json"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class LifxControlError(Exception):
    """Custom exception for LIFX control errors."""
    pass

class LifxController:
    def __init__(self):
        self.lifx = LifxLAN()
        self.config_path = Path(CONFIG_FILE)
        self.config = self.load_config()

    def load_config(self):
        """Load the configuration file if it exists."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {'devices': {}}

    def save_config(self):
        """Save the current configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def is_valid_mac(self, mac):
        """Validate MAC address format."""
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(mac_pattern.match(mac))

    def is_valid_ip(self, ip):
        """Validate IP address format."""
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        if not ip_pattern.match(ip):
            return False
        return all(0 <= int(part) <= 255 for part in ip.split('.'))

    def save_device_manually(self, ip, mac, name):
        """Manually save a device to the configuration."""
        # Validate IP address
        if not self.is_valid_ip(ip):
            raise ValueError(f"Invalid IP address format: {ip}")

        # Validate MAC address
        if not self.is_valid_mac(mac):
            raise ValueError(f"Invalid MAC address format: {mac}")

        # Check if name already exists
        for existing_mac, info in self.config['devices'].items():
            if info['name'].lower() == name.lower():
                raise ValueError(f"Device name '{name}' already exists")

        # Normalize MAC address to lowercase
        mac = mac.lower()

        # Save the device
        self.config['devices'][mac] = {
            'name': name,
            'ip': ip
        }
        self.save_config()
        print(f"Device '{name}' saved successfully with IP: {ip} and MAC: {mac}")

    def discover_devices(self):
        """Discover LIFX devices and prompt for names."""
        print("Discovering LIFX devices...")
        devices = self.lifx.get_lights()
        
        for device in devices:
            mac_addr = device.get_mac_addr()
            ip_addr = device.get_ip_addr()
            
            if mac_addr not in self.config['devices']:
                print(f"\nFound new device:")
                print(f"MAC Address: {mac_addr}")
                print(f"IP Address: {ip_addr}")
                
                name = input("Enter a name for this device (or press Enter to skip): ").strip()
                if name:
                    self.config['devices'][mac_addr] = {
                        'name': name,
                        'ip': ip_addr
                    }
                    print(f"Device '{name}' added to configuration.")
        
        self.save_config()
        print("\nDevice discovery complete.")

    def get_device_by_name(self, name):
        """Get device info by name."""
        for mac, info in self.config['devices'].items():
            if info['name'].lower() == name.lower():
                return mac, info
        return None, None

    def list_devices(self):
        """List all configured devices."""
        if not self.config['devices']:
            print("No devices configured.")
            return

        print("\nConfigured Devices:")
        print("-" * 60)
        print(f"{'Name':<20} {'IP Address':<15} {'MAC Address':<17}")
        print("-" * 60)
        for mac, info in self.config['devices'].items():
            print(f"{info['name']:<20} {info['ip']:<15} {mac:<17}")

    def retry_command(self, light, command_func, *args):
        """Retry a command with exponential backoff."""
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    print(f"Retry attempt {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                return command_func(light, *args)
            except WorkflowException as e:
                last_exception = e
                print(f"Communication error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                # Try to refresh the connection
                try:
                    light.refresh()
                except Exception:
                    pass
            except ValueError as e:
                raise LifxControlError(f"Invalid parameter: {e}")
            except Exception as e:
                raise LifxControlError(f"Unexpected error: {e}")
        
        raise LifxControlError(f"Failed after {MAX_RETRIES} attempts: {last_exception}")

    def execute_power_command(self, light, power_state):
        """Execute power command with proper error handling."""
        def power_command(light, state):
            light.set_power(state)
            # Verify the power state change
            time.sleep(0.5)  # Give the bulb time to respond
            current_power = light.get_power()
            if bool(current_power) != bool(state):
                raise WorkflowException("Power state verification failed")
        
        self.retry_command(light, power_command, power_state)

    def execute_brightness_command(self, light, brightness):
        """Execute brightness command with proper error handling."""
        def brightness_command(light, level):
            light.set_brightness(level)
            # Verify the brightness change
            time.sleep(0.5)
            current_brightness = light.get_color()[2]  # brightness is the third component
            if abs(current_brightness - level) > 100:  # Allow small variation
                raise WorkflowException("Brightness verification failed")
        
        self.retry_command(light, brightness_command, brightness)

    def execute_color_command(self, light, hue, saturation, brightness, kelvin):
        """Execute color command with proper error handling."""
        def color_command(light, h, s, b, k):
            light.set_color([h, s, b, k])
            # Verify the color change
            time.sleep(0.5)
            current_color = light.get_color()
            if any(abs(current - target) > 100 for current, target in 
                  zip(current_color, [h, s, b, k])):  # Allow small variation
                raise WorkflowException("Color verification failed")
        
        self.retry_command(light, color_command, hue, saturation, brightness, kelvin)

    def get_device_status(self, light):
        """Get device status with retry mechanism."""
        def status_command(light):
            power = light.get_power()
            color = light.get_color()
            return power, color
        
        return self.retry_command(light, status_command)

    def execute_command(self, name, command, *args):
        """Execute a command on a specific device with enhanced error handling."""
        mac, info = self.get_device_by_name(name)
        if not mac:
            print(f"Device '{name}' not found in configuration.")
            return

        try:
            light = Light(mac, info['ip'])
            
            try:
                print(f"Connecting to {name} ({info['ip']}, {mac})...")
                light.get_label()  # Test connection
            except WorkflowException:
                print("Initial connection failed. Attempting to rediscover device...")
                # Try to rediscover the device
                devices = self.lifx.get_lights()
                found_device = next((dev for dev in devices if dev.get_mac_addr() == mac), None)
                if found_device:
                    info['ip'] = found_device.get_ip_addr()
                    self.config['devices'][mac]['ip'] = info['ip']
                    self.save_config()
                    print(f"Updated IP address for {name} to {info['ip']}")
                    light = Light(mac, info['ip'])
                else:
                    raise LifxControlError(f"Could not find device {name} on the network")

            if command == "on":
                self.execute_power_command(light, True)
            elif command == "off":
                self.execute_power_command(light, False)
            elif command == "setBrightness":
                if not args:
                    raise LifxControlError("Brightness value (0-65535) required.")
                try:
                    brightness = int(args[0])
                    if not 0 <= brightness <= 65535:
                        raise ValueError("Brightness must be between 0 and 65535")
                    self.execute_brightness_command(light, brightness)
                except ValueError as e:
                    raise LifxControlError(str(e))
            elif command == "setColor":
                if len(args) < 4:
                    raise LifxControlError(
                        "Color requires 4 values: hue (0-65535), saturation (0-65535), "
                        "brightness (0-65535), kelvin (2500-9000)"
                    )
                try:
                    hue, saturation, brightness, kelvin = map(int, args[:4])
                    if not all(0 <= x <= 65535 for x in [hue, saturation, brightness]):
                        raise ValueError("Hue, saturation, and brightness must be between 0 and 65535")
                    if not 2500 <= kelvin <= 9000:
                        raise ValueError("Kelvin must be between 2500 and 9000")
                    self.execute_color_command(light, hue, saturation, brightness, kelvin)
                except ValueError as e:
                    raise LifxControlError(str(e))
            elif command == "status":
                power, color = self.get_device_status(light)
                print(f"\nStatus for {name}:")
                print(f"Power: {'ON' if power else 'OFF'}")
                print(f"Color:")
                print(f"  Hue: {color[0]}")
                print(f"  Saturation: {color[1]}")
                print(f"  Brightness: {color[2]}")
                print(f"  Kelvin: {color[3]}")
            else:
                raise LifxControlError(f"Unknown command: {command}")
            
            print(f"Command '{command}' executed successfully on '{name}'")
            
        except LifxControlError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print("Try running the discovery process again to update device information:")
            print("  python lifx_controller.py --discover")

def main():
    parser = argparse.ArgumentParser(description="LIFX Bulb Controller")
    parser.add_argument("--discover", action="store_true", help="Discover and configure new devices")
    parser.add_argument("--save-device", nargs=3, metavar=('IP', 'MAC', 'NAME'),
                       help="Manually save a device with IP, MAC address, and name")
    parser.add_argument("--list", action="store_true", help="List all configured devices")
    parser.add_argument("--name", help="Device name to control")
    parser.add_argument("--command", help="Command to execute (on, off, setBrightness, setColor, status)")
    parser.add_argument("--args", nargs="*", help="Additional arguments for the command")

    args = parser.parse_args()
    controller = LifxController()

    try:
        if args.discover:
            controller.discover_devices()
        elif args.save_device:
            ip, mac, name = args.save_device
            controller.save_device_manually(ip, mac, name)
        elif args.list:
            controller.list_devices()
        elif args.name and args.command:
            controller.execute_command(args.name, args.command, *(args.args or []))
        else:
            parser.print_help()
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()