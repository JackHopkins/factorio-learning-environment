import cv2
import numpy as np
from typing import Tuple, Optional
import psutil
import pyautogui
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass

from fle.commons.cluster_ips import get_local_container_ips
from fle.cluster.remote.factorio_server_login import get_uninitialised_ips
from screeninfo import get_monitors


@dataclass
class UIElement:
    name: str
    image_path: str
    confidence: float = 0.7
    timeout: int = 10


def launch_factorio():
    # Check to see if Factorio is open
    if not any(process.name() == "factorio" for process in psutil.process_iter()):
        # Launch Factorio if it's not running
        print("Launching Factorio...")
        # Adjust the path to your Factorio executable
        subprocess.Popen(["open", "-a", "Factorio"])
        time.sleep(10)  # Wait for Factorio to start up


def focus_factorio():
    # Use AppleScript to focus Factorio
    applescript = """
    tell application "Factorio" to activate
    """
    subprocess.run(["osascript", "-e", applescript])
    time.sleep(1)  # Wait a moment for the window to come into focus


class FactorioAutomation:
    def __init__(self, assets_dir: str = "assets", monitor_index: int = 0):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(exist_ok=True)

        self.monitor = get_monitors()[monitor_index]
        # Handle negative coordinates
        self.monitor_region = (
            max(0, self.monitor.x),  # Ensure x is not negative
            max(0, self.monitor.y),  # Ensure y is not negative
            self.monitor.width,
            self.monitor.height,
        )

        # Store offset for click adjustment
        self.x_offset = self.monitor.x
        self.y_offset = self.monitor.y

        # Define UI elements
        self.ui_elements = {
            "multiplayer": UIElement("Multiplayer", "multiplayer_button.png", 0.9),
            "connect_address": UIElement(
                "Connect to Address", "connect_to_address_button.png", 0.9
            ),
            "ip_field": UIElement("IP Field", "ip_field.png", 0.85),
            "connect": UIElement("Connect", "connect_button.png", 0.9),
            "quit": UIElement("Quit", "quit_button.png", 0.9),
        }

    def verify_assets(self) -> bool:
        """Verify all required UI element images exist."""
        missing = []
        for element in self.ui_elements.values():
            if not (self.assets_dir / element.image_path).exists():
                missing.append(element.image_path)

        if missing:
            print(f"Missing required assets: {', '.join(missing)}")
            return False
        return True

    def locate_element(self, element: UIElement) -> Optional[Tuple[int, int]]:
        """
        Locate UI element using template matching with OpenCV.
        Returns center coordinates if found, None otherwise.
        """
        try:
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Load template
            template = cv2.imread(str(self.assets_dir / element.image_path))

            # Template matching
            result = cv2.matchTemplate(screenshot_np, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val >= element.confidence:
                h, w = template.shape[:2]
                center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                return center

        except Exception as e:
            print(f"Error locating {element.name}: {str(e)}")

        return None

    def locate_and_click(self, element: UIElement) -> bool:
        start_time = time.time()
        while time.time() - start_time < element.timeout:
            try:
                location = pyautogui.locateOnWindow(  # ).locateCenterOnScreen(
                    str(self.assets_dir / element.image_path),
                    "Factorio 1.1.110",
                    confidence=element.confidence,
                    region=self.monitor_region,
                )
                if location:
                    # Adjust click coordinates for monitor offset
                    click_x = location[0] + (self.x_offset if self.x_offset < 0 else 0)
                    click_y = location[1] + (self.y_offset if self.y_offset < 0 else 0)
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.5)
                    return True
            except pyautogui.ImageNotFoundException:
                pass
            time.sleep(0.5)

        print(f"Could not find {element.name} after {element.timeout} seconds")
        return False

    def connect_to_server(self, ip_address: str, udp: int = 34197) -> bool:
        """Connect to Factorio server using image recognition."""
        if not self.verify_assets():
            return False

        focus_factorio()

        # Reset to main menu
        for _ in range(3):
            pyautogui.press("esc")
            time.sleep(0.5)

        # Click through menu sequence
        for element in ["multiplayer", "connect_address", "ip_field"]:
            if not self.locate_and_click(self.ui_elements[element]):
                raise Exception(f"Could not find element - {element}")

        # Enter IP address
        pyautogui.hotkey("command", "a")
        pyautogui.press("delete")
        pyautogui.write(f"{ip_address}:{udp}")

        # Connect and wait
        if not self.locate_and_click(self.ui_elements["connect"]):
            return False

        time.sleep(5)

        # Exit sequence
        pyautogui.press("esc")
        return self.locate_and_click(self.ui_elements["quit"])


def main():
    # Display available monitors

    ips, udp_ports, tcp_ports = get_local_container_ips()
    if not ips:
        raise RuntimeError("No local container IPs found")

    ip_addresses = get_uninitialised_ips(ips, tcp_ports)
    launch_factorio()

    monitors = get_monitors()
    print("Available monitors:")
    for i, m in enumerate(monitors):
        print(f"{i}: {m.name} ({m.width}x{m.height} at ({m.x}, {m.y}))")

    for monitor_index in [1]:
        print(f"\nAttempting to connect on monitor {monitors[monitor_index].name}...")
        automation = FactorioAutomation(monitor_index=monitor_index)

        for ip, udp in zip(ip_addresses, udp_ports):
            success = automation.connect_to_server(ip, udp)
            print(
                f"{'Successfully connected to' if success else 'Failed to connect to'} {ip}"
            )


if __name__ == "__main__":
    main()
