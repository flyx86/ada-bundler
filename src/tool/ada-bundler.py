#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import sys
import shutil
import os
import os.path
import yaml
import struct

# ----------
# Functions for retrieving values from the configuration file
# ----------

def singleValue(containingName, containing, key, required=False):
    if not containing.has_key(key):
        if required:
            raise Exception("Missing key: {0}.{1}".format(containingName, key))
        else:
            value = ""
    else:
        value = containing[key]
    if not isinstance(value, str):
        raise Exception("Expected single string value for {0}".format(key))
    return value

def listValue(containingName, containing, key, required=False):
    if not containing.has_key(key):
        if required:
            raise Exception("Missing key: {0}.{1}".format(containingName, key))
        else:
            value = []
    else:
        value = containing[key]
    if isinstance(value, str):
        return list(containing[key])
    if not isinstance(value, list):
        raise Exception("Expected list value for {0}".format(key))
    return value

def dictValue(containingName, containing, key, required=False):
    if not containing.has_key(key):
        if required:
            raise Exception("Missing key: {0}.{1}".format(containingName, key))
        else:
            value = {}
    else:
        value = containing[key]
    if not isinstance(value, dict):
        raise Exception("Expected dict value for {0}".format(key))
    return value

# ----------
# Classes representing the configuration
# ----------
    
class Target (object):
    OSX     = 0
    Windows = 1
    Linux   = 2

class ConfigValues (object):
    
    def __init__(self, setname, **kwargs):
        self._config_files = listValue(setname, kwargs, "configuration")
        self._data_files   = listValue(setname, kwargs, "data")
        self._executable   = singleValue(setname, kwargs, "executable")


class OsxConfigValues (ConfigValues):
    
    def __init__(self, **kwargs):
        super(OsxConfigValues, self).__init__("osx", **kwargs)
        
        self._icon_file  = singleValue("osx", kwargs, "icon", True)
        self._identifier = singleValue("osx", kwargs, "identifier", True)
        if not os.path.exists(self._icon_file) or not os.path.isfile(self._icon_file):
            raise Exception("Icon file {0} doesn't exist!".format(self._icon_file))
        self._custom_info_plist = singleValue("osx", kwargs, "custom-info", False)
    
    @property
    def icon(self):
        return self._icon_file
    
    @property
    def identifier(self):
        return self._identifier
    
    @property
    def custom_info_plist(self):
        return self._custom_info_plist
    
            
class WindowsConfigValues (ConfigValues):
    
    def __init__(self, **kwargs):
        super(WindowsConfigValues, self).__init__("windows", **kwargs)
        
        self._icon_file = singleValue("windows", kwargs, "icon", True)
        if not os.path.exists(self._icon_file) or not os.path.isfile(self._icon_file):
            raise Exception("Icon file {0} doesn't exist!".format(self._icon_file))
    
    @property
    def icon(self):
        return self._icon_file

class LinuxConfigValues (ConfigValues):
    
    def __init__(self, **kwargs):
        super(LinuxConfigValues, self).__init__("linux", **kwargs)


class Configuration (ConfigValues):
    
    def __init__(self, file, target):
        contents = file.read()
        values = yaml.safe_load (contents)
        if values is None:
            values = {}
        super(Configuration, self).__init__("global", **values)
        
        self.osx     = OsxConfigValues(**dictValue("global", values, "osx"))
        self.windows = WindowsConfigValues(**dictValue("global", values, "windows"))
        self.linux   = LinuxConfigValues(**dictValue("global", values, "linux"))
        
        self._target = target
        self._destination = singleValue("global", values, "name", True)
        self._version = singleValue("global", values, "version", True)

    @property
    def config_files(self):
        if self._target == Target.OSX:
            return self._config_files + self.osx._config_files
        if self._target == Target.Windows:
            return self._config_files + self.windows._config_files
        if self._target == Target.Linux:
            return self._config_files + self.linux._config_files
        
        raise Exception("Unknown Target: {0}".format(self._target))
    
    @property
    def data_files(self):
        if self._target == Target.OSX:
            return self._data_files + self.osx._data_files
        if self._target == Target.Windows:
            return self._data_files + self.windows._data_files
        if self._target == Target.Linux:
            return self._data_files + self.linux._data_files
    
    @property
    def resource_destination(self):
        if self._target == Target.OSX:
            return self._destination + ".app/Contents/Resources"
        else:
            return self._destination
    
    @property
    def config_destination(self):
        return os.path.join(self.resource_destination, "config")
    
    @property
    def data_destination(self):
        return os.path.join(self.resource_destination, "data")
    
    @property
    def base_destination(self):
        if self._target == Target.OSX:
            return self._destination + ".app"
        else:
            return self._destination
    
    @property
    def executables(self):
        if self._executable:
			if self._target == Target.Windows:
				value = self._executable + ".exe"
			else:
				value = self._executable
        elif self._target == Target.OSX:
            value = self.osx._executable
        elif self._target == Target.Windows:
            value = self.windows._executable + ".exe"
        elif self._target == Target.Linux:
            value = self.linux._executable
        if not value:
            raise Exception("No executable defined for your target")
        return [value]
    
    @property
    def executable_dir(self):
        if self._target == Target.OSX:
            return os.path.join(self.base_destination, "Contents/MacOS")
        else:
            return self.base_destination
    
    @property
    def target(self):
        return self._target
    
    @property
    def name(self):
        return self._destination
    
    @property
    def version(self):
        return self._version

# ----------
# Utility functions
# ----------

def copy_files(pathList, destination):
    for path in pathList:
        print("Copying {0}".format(path))
        if os.path.isfile(path):
            shutil.copy(path, destination)
        elif os.path.isdir(path):
            (head, tail) = os.path.split(path)
            shutil.copytree(path, os.path.join(destination, tail))
        else:
            sys.stderr.write("Path not valid: {0}\n".format(path))


def load_configuration():
    if len(sys.argv) > 1:
        configPath = sys.argv[1]
    else:
        configPath = "bundle.yaml"
    if len(sys.argv) > 2:
        if sys.argv[2].lower() == "osx":
            target = Target.OSX
        elif sys.argv[2].lower() == "windows":
            target = Target.Windows
        elif sys.argv[2].lower() == "linux":
            target = Target.Linux
        else:
            raise Exception("Unknown target: {0}".format(sys.argv[2]))
    else:
        if sys.platform.startswith("linux"):
            target = Target.Linux
        elif sys.platform == "win32" or sys.platform == "cygwin":
            target = Target.Windows
        elif sys.platform == "darwin":
            target = Target.OSX
        else:
            raise Exception("Unsupported platform: {0}. Please specify a supported platform explicitly.".format(sys.platform))
    
    try:
        file = open(configPath, 'r')
    except IOError:
        raise Exception("Could not load configuration file {0}".format(configPath))
    configuration = Configuration(file, target)
    file.close()
    return configuration

# ----------
# OSX specific
# ----------

info_plist_template = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en-us</string>
    <key>CFBundleTypeIconFile</key>
    <string>docplaintext</string>
    <key>CFBundleTypeName</key>
    <string>Plain Text</string>
    <key>CFBundleExecutable</key>
    <string>{executable}</string>
    <key>CFBundleIconFile</key>
    <string>{iconfile}</string>
    <key>CFBundleIdentifier</key>
    <string>{identifier}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{name}</string>
    <key>CFBundlePackageType</key>
    <string>AAPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
{custom}
</dict>
</plist>"""

# ----------
# Windows specific
# ----------

def updateExecutableIcon(executablePath, iconPath):
    """
    Updates the icon of a Windows executable file.
    """
    
    import win32api, win32con

    handle = win32api.BeginUpdateResource(executablePath, False)

    icon = open(iconPath, "rb")

    fileheader = icon.read(6)

    # Read icon data
    image_type, image_count = struct.unpack("xxHH", fileheader)

    icon_group_desc = struct.pack("<HHH", 0, image_type, image_count)
    icon_sizes = []
    icon_offsets = []

    # Read data of all included icons
    for i in range(1, image_count + 1):
        imageheader = icon.read(16)
        width, height, colors, panes, bits_per_pixel, image_size, offset = struct.unpack("BBBxHHLL", imageheader)

        icon_group_desc = icon_group_desc + struct.pack("<BBBBHHIH",
            width,          # Icon width
            height,         # Icon height
            colors,         # Colors (0 for 256 colors)
            0,              # Reserved2 (must be 0)
            panes,          # Color planes
            bits_per_pixel, # Bits per pixel
            image_size,     # ImageSize
            i               # Resource ID
        )
        icon_sizes.append(image_size)
        icon_offsets.append(offset)

    # Read icon content and write it to executable file
    for i in range(1, image_count + 1):
        icon_content = icon.read(icon_sizes[i - 1])
        win32api.UpdateResource(handle, win32con.RT_ICON, i, icon_content)

    win32api.UpdateResource(handle, win32con.RT_GROUP_ICON, "MAINICON", icon_group_desc)

    win32api.EndUpdateResource(handle, False)

# ----------
# Main routine
# ----------

configuration = load_configuration()
if os.path.exists(configuration.base_destination):
    shutil.rmtree(configuration.base_destination)

for path in [configuration.executable_dir, configuration.config_destination,
             configuration.data_destination]:
    if not os.path.exists(path):
        os.makedirs(path)

copy_files(configuration.config_files, configuration.config_destination)
copy_files(configuration.data_files, configuration.data_destination)
copy_files(configuration.executables, configuration.executable_dir)

if configuration.target == Target.OSX:
    copy_files([configuration.osx.icon], configuration.resource_destination)
    (head, tail) = os.path.split(configuration.executables[0])
    info_plist = open(os.path.join(configuration.base_destination, "Contents/Info.plist"), 'w')
    info_plist.write(info_plist_template.format(
            executable = tail,
            iconfile   = configuration.osx.icon,
            identifier = configuration.osx.identifier,
            name       = configuration.name,
            version    = configuration.version,
            custom     = configuration.osx.custom_info_plist))
    info_plist.close()
elif configuration.target == Target.Windows:
    head, tail = os.path.split(configuration.executables[0])
    executableTargetPath = os.path.join(configuration.executable_dir, tail)
    updateExecutableIcon(executableTargetPath, configuration.windows.icon)