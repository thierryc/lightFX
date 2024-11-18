# lifx_controller - LIFX Bulb Controller

A Python-based command-line tool for discovering, configuring, and controlling LIFX smart bulbs on your local network. This tool provides an easy way to manage your LIFX devices, including manual configuration and various control options.

## Features

- 🔍 Automatic device discovery on local network
- ⚙️ Manual device configuration with IP and MAC address
- 💡 Complete bulb control (power, brightness, color)
- 📝 Configuration persistence in JSON format
- 📊 Device listing and status monitoring
- ✅ Input validation for IP and MAC addresses
- 🔒 Error handling and user feedback

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YourUsername/lifx-controller.git
cd lifx-controller
```

2. Install required dependencies:
```bash
pip install lifxlan
```
or 

```bash
pip install -r requirements.txt
```

## Usage

### Device Discovery and Configuration

**Automatic Discovery:**
```bash
python lifx_controller.py --discover
```
This will scan your network for LIFX devices and prompt you to name each new device found.

**Manual Device Configuration:**
```bash
python lifx_controller.py --save-device <IP> <MAC> <NAME>
```
Example:
```bash
python lifx_controller.py --save-device 192.168.1.100 d0:73:d5:01:02:03 "Living Room"
```

Optional:
```bash
chmod +x lifx_controller.py
```   

**List Configured Devices:**
```bash
python lifx_controller.py --list
```

### Device Control

**Power Control:**
```bash
# Turn on
python lifx_controller.py --name "Living Room" --command on

# Turn off
python lifx_controller.py --name "Living Room" --command off
```

**Brightness Control:**
```bash
# Set brightness (0-65535)
python lifx_controller.py --name "Living Room" --command setBrightness --args 32768
```

**Color Control:**
```bash
# Set color (hue, saturation, brightness, kelvin)
python lifx_controller.py --name "Living Room" --command setColor --args 32768 65535 65535 3500
```

**Device Status:**
```bash
python lifx_controller.py --name "Living Room" --command status
```

## Configuration File

The tool stores device configurations in `lifx_config.json`. Example structure:
```json
{
  "devices": {
    "d0:73:d5:01:02:03": {
      "name": "Living Room",
      "ip": "192.168.1.100"
    }
  }
}
```

## Command Reference

| Command | Description | Arguments |
|---------|-------------|-----------|
| `--discover` | Scan network for LIFX devices | None |
| `--save-device` | Manually add a device | `<IP> <MAC> <NAME>` |
| `--list` | Show all configured devices | None |
| `--name` | Specify device for control | Device name |
| `--command` | Control command to execute | Command name |
| `--args` | Command arguments | Varies by command |

### Available Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `on` | None | Turn device on |
| `off` | None | Turn device off |
| `setBrightness` | `<value>` | Set brightness (0-65535) |
| `setColor` | `<hue> <saturation> <brightness> <kelvin>` | Set color properties |
| `status` | None | Show device status |

## Error Handling

The tool includes validation for:
- IP address format
- MAC address format
- Device name conflicts
- Network connectivity
- Command execution

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Requirements

- Python 3.6 or higher
- lifxlan library
- Network access to LIFX devices

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [lifxlan](https://github.com/mclarkk/lifxlan)
- Inspired by the LIFX HTTP API

## Authors

- Thierryc - *Initial work* - [thierryc](https://github.com/thierryc)

## Support

If you encounter any issues or have questions, please:
1. Check the [Issues](https://github.com/YourUsername/lifx-controller/issues) page
2. Create a new issue if your problem isn't already listed

## Known Issues

### Discovery + Use Appears to Fail on LIFX Firmware 3.70

#### Problem
Some users have reported issues with the `lifxlan` library failing to discover and control LIFX devices running Firmware 3.70. This problem may occur due to outdated MAC address mappings or compatibility quirks introduced in this firmware version.

The exact root cause of the issue remains unclear.

#### Affected Versions
- Firmware: 3.70
- lifxlan: Any version

#### Symptoms
- Devices are not discoverable.
- Commands to control devices fail.

#### Workaround / Solution

1. **Update MAC Address Mapping**
   Use the official LIFX app or Apple Home to update the MAC address of your device on the network. 
   This may help the device has been re-registered correctly with your router.

2. **Retry Discovery**
   After updating the MAC address:
   - Restart your LIFX devices.
   - Retry `lifx_controller`.

---

Made with ❤️ for the LIFX community