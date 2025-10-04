#!/usr/bin/env python3
"""
Render deployment startup script
"""

import os
import sys
from nse_monitor import NSEMonitorService

if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create and start monitor
    monitor = NSEMonitorService()
    monitor.start()