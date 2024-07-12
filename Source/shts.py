#------------------------------------------------------------------------------#
# SHTS - V2                                                                    #
# Author: Marijn van Tricht                                                    #
# Last saved at: 05/07/2024                                                    #
#                                                                              #
# expanding on wxexample for cef from cztomczak                                #
#------------------------------------------------------------------------------#

# Imports ---------------------------------------------------------------------#
import platform
import sys
import os
import ctypes
import importlib
import time

import shutil
import tempfile

import asyncio
import threading
import socket
import json
import websockets
from websockets.server import serve

from cefpython3 import cefpython as cef

import wx
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

if sys.platform == 'darwin':
    from AppKit import NSApplication, NSApp, NSWindow
    
if sys.platform == 'linux':
    import gi
    from gi.repository import Gtk, Gdk

# Settings -------------------------------------------------------------------#

global save_before
global disable_save_warning
global allow_network_access
global open_DevTools
global color

# If active path is changed, show dialog to save before (at creation) [true]
# or after (at closing) [false]
save_before = False

# Disable save warning for not saving an unsaved file
disable_save_warning = False

# By default no access to the network
allow_network_access = [False,False]

# Start with the debugger
open_DevTools = False

# Main color
color = "#7D8491"

# Set environment variables to enable file access
os.environ["CEF_ALLOW_FILE_ACCESS_FROM_FILES"] = "0"
os.environ["CEF_ALLOW_UNIVERSAL_ACCESS_FROM_FILES"] = "0"

# Globals ---------------------------------------------------------------------#

# Platforms
WINDOWS = (platform.system() == "Windows")
LINUX = (platform.system() == "Linux")
MAC = (platform.system() == "Darwin")

if MAC:
    try:
        # noinspection PyUnresolvedReferences
        from AppKit import NSApp
    except ImportError:
        print("[wxpython.py] Error: PyObjC package is missing, "
              "cannot fix Issue #371")
        print("[wxpython.py] To install PyObjC type: "
              "pip install -U pyobjc")
        sys.exit(1)

# Configuration
WIDTH = 900
HEIGHT = 640

# Globals
g_count_windows = 0
ws_port = None
websocket_server = None
instance = None
filenameInput = "index.shts"

# Functions -------------------------------------------------------------------#

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Dialog using Tk
def saveDialog():
    root = tk.Tk()
    root.withdraw()
    root.iconbitmap(resource_path("shts.ico"))
    filepath = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[
            ("SHTS file", "*.shts"),
            ("shtml file", "*.shtml"),
            ("All files", "*.*")]
    )
    if filepath:
        return filepath
    else:
        print("Save file dialog was canceled.")
        return None

def check_versions():
    print("[wxpython.py] CEF Python {ver}".format(ver=cef.__version__))
    print("[wxpython.py] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]))
    print("[wxpython.py] wxPython {ver}".format(ver=wx.version()))
    # CEF Python version requirement
    assert cef.__version__ >= "66.0", "CEF Python v66.0+ required to run this"

def scale_window_size_for_high_dpi(width, height):
    """Scale window size for high DPI devices. This func can be
    called on all operating systems, but scales only for Windows.
    If scaled value is bigger than the work area on the display
    then it will be reduced."""
    if not WINDOWS:
        return width, height
    (_, _, max_width, max_height) = wx.GetClientDisplayRect().Get()
    # noinspection PyUnresolvedReferences
    (width, height) = cef.DpiAware.Scale((width, height))
    if width > max_width:
        width = max_width
    if height > max_height:
        height = max_height
    return width, height

def allow_network_access_callback(value, port=None, bridge_info=None):
    global allow_network_access
    global instance
    allow_network_access = [True, value]
    if port is not None:
        if allow_network_access[1]:
            instance.server.open(port, bridge_info)

def file_save_confirmation_callback(value):
    global instance
    if value == True:
        instance.skip_unload = True
        instance.mainframe.Close()

# Classes ---------------------------------------------------------------------#

class Interface():
    def startServer(self, port, bridge_info=None):
        global instance
        global allow_network_access
        if not allow_network_access[0]:
            callback = lambda value: allow_network_access_callback(
                value, port, bridge_info)
            
            instance.confirmationDialog(
                "Allow network access",
                "This script uses network access.\n\
                Allow network access during this sessions?",
                callback,
                "Allow",
                "Deny")
        if allow_network_access[1]:
            return instance.server.open(port, bridge_info)
        else:
            return None

    def stopServer(self):
        global instance
        return instance.server.close()

    def save(self, content):
        global instance
        result = instance.save(content)
        instance.mainframe.open(instance.filename)
        return result

    def new(self, content, callback=None, error_callback=None):
        global instance
        return instance.changeActiveFilepath(content)

class WebSocketServer:
    def __init__(self):
        self.host = 'localhost'
        self.port = 12345
        self.running = False
        self.server_loop = None
        self.server_thread = None
        self.server_future = None

        self.tcp_server = TCPServer(self)
        self.udp_server = UDPServer(self)

        self.connections = set()

    async def echo(self, websocket, path):
        self.connections.add(websocket)
        try:
            async for message in websocket:
                await self.broadcast(message, websocket)
                self.tcp_server.send(message)
                self.udp_server.send(message)
        except:
            pass
        finally:
            self.connections.remove(websocket)

    async def broadcast(self, message, sender):
        for connection in self.connections:
            if connection != sender:
                await connection.send(message)

    async def run_server(self):
        self.server_future = asyncio.Future()
        print(f"Webserving localhost @ {self.port}")
        async with serve(self.echo, self.host, self.port):
            await self.server_future
        self.running = False

    def create_and_run(self):
        self.server_loop.run_until_complete(self.run_server())

    def open(self, port, bridge_info):
        self.port = port
        
        if self.running is False:
            self.running = True
            self.server_loop = asyncio.new_event_loop()
            self.server_thread = threading.Thread(target=self.create_and_run)
            self.server_thread.start()
        else:
            self.close()
            self.open(port, bridge_info)

        if bridge_info is not None and bridge_info != "":
            try:
                if bridge_info["protocol"].lower() == 'udp':
                    inport = None
                    if "inport" in bridge_info:
                        inport = bridge_info["inport"]
                    outport = None
                    if "outport" in bridge_info:
                        outport = bridge_info["outport"]
                    print(f"UDP Protocol - InPort: {inport}, OutPort: {outport}")
                    self.bridge_udp(inport, outport)
                elif bridge_info["protocol"].lower() == 'tcp':
                    port = bridge_info["port"]
                    print(f"TCP Protocol - Port: {port}")
                    self.bridge_tcp(port)
                else:
                    print(f"Unknown protocol: {bridge_info}")
            except:
                print(f"Error occurred during the evaluation of the argument \
containing the bridge info: {bridge_info}")

    def close(self):
        if self.running:
            self.tcp_server.close()
            self.udp_server.close()
            
            self.server_loop.call_soon_threadsafe(
                self.server_future.set_result, True)

            if self.server_thread:
                self.server_thread.join()

            self.server_loop.stop()
            self.server_loop = None
            
            self.server_thread = None
            self.server_future = None

            print("Closed server.")

    def bridge_udp(self, inport, outport):
        self.udp_server.open(inport, outport)

    def bridge_tcp(self, port):
        self.tcp_server.open(port)

    async def handle_tcp_message(self, message):
        if self.connections:
            tasks = [websocket.send(message) for websocket in self.connections]
            await asyncio.gather(*tasks)

    async def handle_udp_message(self, message):
        if self.connections:
            tasks = [websocket.send(message) for websocket in self.connections]
            await asyncio.gather(*tasks)

    def _handle_tcp_message(self, message):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.handle_tcp_message(message))        

    def _handle_udp_message(self, message):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.handle_udp_message(message)) 

class TCPServer:
    def __init__(self, websocket_server):
        self.server_socket = None
        self.server_thread = None
        self.running = False
        self.websocket_server = websocket_server
        self.clients = []

    def open(self, port):
        if self.server_socket is None:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('localhost', port))
            self.server_socket.listen(5)
            self.running = True
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.start()
            print(f"TCP server started on port {port}")
        else:
            self.close()
            self.open(port)

    def run_server(self):
        while self.running:
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection from {client_address}")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client,
                             args=(client_socket,)).start()

    def handle_client(self, client_socket):
        with client_socket:
            while True:
                message = client_socket.recv(1024)
                if not message:
                    break
                print(f"TCP Server received message: {message.decode('utf-8')}")
                self.websocket_server._handle_tcp_message(message)
                self.send(message, sender=client_socket)

        self.clients.remove(client_socket)

    def send(self, message):
        if self.clients:
            for client in self.clients:
                client.send(message)

    def close(self):
        if self.server_socket is not None:
            self.running = False
            self.server_socket.close()
            self.server_thread.join()
            for client in self.clients:
                client.close()
            self.server_socket = None
            print("TCP server stopped")

class UDPServer:
    def __init__(self, websocket_server=None):
        self.server_socket = None
        self.server_thread = None
        self.running = False
        self.websocket_server = websocket_server
        self.outport = None

    def open(self, inport, outport):
        if self.server_socket is None:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if inport is not None:
                try:
                    self.server_socket.bind(('localhost', inport))
                    self.running = True
                    self.server_thread = threading.Thread(target=self.run_server)
                    self.server_thread.start()
                except OSError as e:
                    print(f"Failed to bind to port {inport}: {e}")
                    self.server_socket.close()
            self.outport = outport
            print(f"UDP server started on port {inport} and prepared to send to port {outport}")
        else:
            self.close()
            self.open(inport, outport)

    def run_server(self):
        try:
            while self.running:
                try:
                    if self.server_socket is not None:
                        message, client_address = self.server_socket.recvfrom(1024)
                        print(f"UDP Server received message: {message.decode('utf-8')} from {client_address}")
                    if self.websocket_server is not None:
                        self.websocket_server._handle_udp_message(message)
                except socket.error:
                    continue
        except Exception as e:
            print(f"Error: {e}")

    def send(self, message):
        if self.outport is not None:
            client_address = ('127.0.0.1', self.outport)
            self.server_socket.sendto(message, client_address)
            print(f"Sent message to {client_address}")

    def close(self):
        if self.server_socket is not None:
            self.running = False
            self.server_socket.close()
            self.server_socket = None
            if self.server_thread is not None:
                self.server_thread.join()
            print("UDP server stopped")

class ClientHandler(object):
    def __init__(self):
        self.filename = ""
        self.status_callback = None

    def OnTitleChange(self, browser, title):
        global instance
        if '<' in title and '>' in title:
            print(f"Warning: <,> in OnTitleChange title")
            instance.updateWindowTitle()
        else: 
            print(f"Title Changed: {title}")
            instance.updateWindowTitle(title)
            
    def OnConsoleMessage(self, browser, message, source, line, level):
        print(f"JavaScript Console: {message}")

    def OnGotFocus(self, browser, **_):
        # Temporary fix for focus issues on Linux (Issue #284).
        if LINUX:
            print("[wxpython.py] FocusHandler.OnGotFocus:"
                  " keyboard focus fix (Issue #284)")
            browser.SetFocus(True)

class SHTS():
    def __init__(self, mainframe, filename):
        self.filename = os.path.abspath(filename)
        self.mainframe = mainframe
        self.originstate = True
        self.skip_unload = False
        self.server = WebSocketServer()

    def save(self, content):
        try:
            oldcontent = ""
            with open(self.filename, 'r') as file:
                oldcontent = file.read()
                
            try:
                print(self.filename)
                with open(self.filename, 'w') as file:
                    file.write(content)
                print(f"File saved successfully to {self.filename}!")
                return "File saved successfully!"
            except Exception as e:
                print(f"Error saving file: {str(e)}")
                try:
                    with open(self.filename, 'w') as file:
                        file.write(oldcontent)
                except Exception as e:
                    print(f"Error saving backup file: {str(e)}")
                    return f"Error saving backup file: {str(e)}"
                return f"Error saving file: {str(e)}"
        except Exception as e:
            print(f"Error during save function: {str(e)}")
            return f"Error during save function: {str(e)}"

    def changeActiveFilepath(self, content):
        print(f"changing active filepath..")
        global save_before
        self.originstate = False
        if save_before:
            print(f"Active filepath set to: {filepath}")
            filepath = saveDialog();
            if filepath is not None:
                self.filename = filepath
                self.mainframe.filename = self.filename
                print(f"filename is {self.filename}")
                self.save(content);

                temp_file_path = os.path.join(self.mainframe.tempdir,
                                              "tempfile.shtml")
                shutil.copyfile(self.filename, temp_file_path)
                        
                self.mainframe.browser.LoadUrl(temp_file_path)
        else:
            self.filename = os.path.join(self.mainframe.tempdir,
                                         "tempfile.shtml")
            self.mainframe.filename = self.filename
            print(f"filename is {self.filename}")
            self.save(content)
            self.mainframe.browser.LoadUrl(self.filename)

    def unload(self):
        global save_before
        global disable_save_warning
        if self.skip_unload:
            self.skip_unload = False
            return True
        
        # Save
        if (not save_before) and (not self.originstate):
            filepath = saveDialog()
            if filepath is not None and self.filename != "":
                shutil.copyfile(self.filename, filepath)
                self.filename = filepath
                self.mainframe.filename = filepath
                print(f"filename is {self.filename}")
                return True
            else:
                if disable_save_warning:
                    return True
                else:
                    return self.confirmationDialog(
                        "Quit?",
                        "You have unsaved changes. Are you sure you want to \
quit?",
                        file_save_confirmation_callback,
                        "Quit",
                        "Cancel")
                    return False
            return False
        return True

    def close(self, value=True):
        if value:
            self.skip_unload = True
            self.mainframe.browser.CloseBrowser(value)
        else:
            self.mainframe.browser.Reload()

    def updateWindowTitle(self, title=""):
        if title and title != "":
            title = "SHTS - " + title
        else:
            title = "SHTS"
        self.mainframe.set_title(title)
        return title

    def confirmationDialog(self, title, message, callback, c1="Yes", c2="No"):
        global color
        js = f"""
(function() {{
    var fontLinkHref = 'https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap';
    var isFontLinkPresent = Array.from(
        document.getElementsByTagName('link')).some(
            link => link.href === fontLinkHref);
            
    if (!isFontLinkPresent) {{
        var link = document.createElement('link');
        link.href = fontLinkHref;
        link.rel = 'stylesheet';
        document.head.appendChild(link);
    }}

    var existingDialog = document.getElementById('__conf-dialog');
    if (existingDialog) {{
        document.body.removeChild(existingDialog);
    }}
                
    var existingBackdrop = document.getElementById('__conf-backdrop');
    if (existingBackdrop) {{
        document.body.removeChild(existingBackdrop);
    }}
                
    var backdrop = document.createElement('div');
    backdrop.id = '__conf-backdrop';
    backdrop.style.position = 'fixed';
    backdrop.style.top = '0';
    backdrop.style.left = '0';
    backdrop.style.width = '100%';
    backdrop.style.height = '100%';
    backdrop.style.backgroundColor = 'rgba(0,0,0,0.5)';
    backdrop.style.zIndex = '999';
    document.body.appendChild(backdrop);

    var div = document.createElement('div');
    div.id = '__conf-dialog';
    div.style.position = 'fixed';
    div.style.top = '50%';
    div.style.left = '50%';
    div.style.transform = 'translate(-50%, -50%)';
    div.style.padding = '20px';
    div.style.backgroundColor = 'white';
    div.style.borderRadius = '8px';
    div.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
    div.style.zIndex = '1000';
    div.style.textAlign = 'center';
    div.style.fontFamily = '"Inter", sans-serif';
    div.style.fontWeight = '400';
    div.innerHTML = `
        <h2 style="margin-top:5px;margin-bottom:5px;color:black;">{title}</h2>
        <p>{message}</p>
        <div style="
        display: flex;
        justify-content:
        space-between;
        color:black;
        width: 100%;">
            <button id="__conf-ok-button" style="
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                flex: 1;
                margin-right: 5px;
                font-family: 'Inter', sans-serif;
                font-weight: 400;
            ">{c1}</button>
            <button id="__conf-cancel-button" style="
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                flex: 1;
                margin-left: 5px;
                font-family: 'Inter', sans-serif;
                font-weight: 400;
            ">{c2}</button>
        </div>
    `;
    document.body.appendChild(div);

    document.getElementById('__conf-ok-button').addEventListener('click',
        function() {{
            window.__callback(true);
            document.body.removeChild(div);
            document.body.removeChild(backdrop);
        }}
    );

    document.getElementById('__conf-cancel-button').addEventListener('click',
        function() {{
            window.__callback(false);
            document.body.removeChild(div);
            document.body.removeChild(backdrop);
        }}
    );
}})();
        """
        self.mainframe.callback = callback
        self.mainframe.browser.GetMainFrame().ExecuteJavascript(js)
        return False
        
class mainFrame(wx.Frame):
    def __init__(self, filename):
        self.filename = filename
        self.tempdir = None
        self.create()

    def create(self):
        if self.tempdir:
            shutil.rmtree(self.tempdir)
        
        self.tempdir = tempfile.mkdtemp()
        self.browser = None
        self.callback = None
        
        global instance
        instance = SHTS(self, self.filename)
        
        # Must ignore X11 errors like 'BadWindow' and others by
        # installing X11 error handlers. This must be done after
        # wx was intialized.
        if LINUX:
            cef.WindowUtils.InstallX11ErrorHandlers()

        global g_count_windows
        g_count_windows += 1

        if WINDOWS:
            # noinspection PyUnresolvedReferences, PyArgumentList
            print("[wxpython.py] System DPI settings: %s"
                  % str(cef.DpiAware.GetSystemDpi()))
        if hasattr(wx, "GetDisplayPPI"):
            print("[wxpython.py] wx.GetDisplayPPI = %s" % wx.GetDisplayPPI())
        print("[wxpython.py] wx.GetDisplaySize = %s" % wx.GetDisplaySize())

        print("[wxpython.py] MainFrame declared size: %s"
              % str((WIDTH, HEIGHT)))
        size = scale_window_size_for_high_dpi(WIDTH, HEIGHT)
        print("[wxpython.py] MainFrame DPI scaled size: %s" % str(size))

        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY,
                          title='SHTS', size=size)
        # wxPython will set a smaller size when it is bigger
        # than desktop size.
        print("[wxpython.py] MainFrame actual size: %s" % self.GetSize())

        self.setup_icon()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Set wx.WANTS_CHARS style for the keyboard to work.
        # This style also needs to be set for all parent controls.
        self.browser_panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.browser_panel.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.browser_panel.Bind(wx.EVT_SIZE, self.OnSize)

        if MAC:
            # Make the content view for the window have a layer.
            # This will make all sub-views have layers. This is
            # necessary to ensure correct layer ordering of all
            # child views and their layers. This fixes Window
            # glitchiness during initial loading on Mac (Issue #371).
            NSApp.windows()[0].contentView().setWantsLayer_(True)

        if LINUX:
            # On Linux must show before embedding browser, so that handle
            # is available (Issue #347).
            self.Show()
            # In wxPython 3.0 and wxPython 4.0 on Linux handle is
            # still not yet available, so must delay embedding browser
            # (Issue #349).
            if wx.version().startswith("3.") or wx.version().startswith("4."):
                wx.CallLater(100, self.embed_browser)
            else:
                # This works fine in wxPython 2.8 on Linux
                self.embed_browser()
        else:
            self.embed_browser()
            self.Show()

        if os.path.isfile(self.filename):
            self.open(self.filename)

    def set_title(self, title):
        self.SetTitle(title)

    def setup_icon(self):
        icon_file = os.path.join(resource_path("shts.ico"))
        icon = wx.Icon(icon_file, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

    def embed_browser(self):
        window_info = cef.WindowInfo()
        (width, height) = self.browser_panel.GetClientSize().Get()
        assert self.browser_panel.GetHandle(), "Window handle not available"
        window_info.SetAsChild(self.browser_panel.GetHandle(),
                               [0, 0, width, height])

        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <style>
        body {
            background-color: %23d3d3d3;
            color: %23a9a9a9;
            font-family: 'Arial', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .centered-text {
            text-align: center;
            color: %23a9a9a9;
        }
    </style>
</head>
<body>
    <div class="centered-text">
        <p>Could not find file """ + os.path.basename(self.filename) + """</p>
        <p>Drag and drop a file to run or run a .shts script with this executable</p>
    </div>
</body>
</html>
"""
        
        self.browser = cef.CreateBrowserSync(window_info,
            url="data:text/html," + html_content)
        
        # Create bindings
        bindings = cef.JavascriptBindings(bindToFrames=False,
                                          bindToPopups=False)
        
        bindings.SetObject("SHTS", Interface())
        bindings.SetFunction("__callback", self.onCallback)
        self.browser.SetJavascriptBindings(bindings)

        # Set client handler
        self.browser.SetClientHandler(ClientHandler())

    def open(self, filename):
        global open_DevTools
        # Buffer content
        shtml_content = ""

        _, ext = os.path.splitext(filename)
        if ext.lower() == ".shts":
            temp_file_path = os.path.join(self.tempdir, "tempfile.shtml")
            try:
                shutil.copyfile(self.filename, temp_file_path)
                self.browser.LoadUrl(temp_file_path)
            except:
                pass
        else:
            self.browser.LoadUrl(filename)        

        if open_DevTools:
            self.browser.ShowDevTools()

    def onCallback(self, value):
        if self.callback:
            self.callback(value)
            self.callback = None

    def OnSetFocus(self, _):
        if not self.browser:
            return
        if WINDOWS:
            cef.WindowUtils.OnSetFocus(self.browser_panel.GetHandle(),
                                       0, 0, 0)
        self.browser.SetFocus(True)

    def OnSize(self, _):
        if not self.browser:
            return
        if WINDOWS:
            cef.WindowUtils.OnSize(self.browser_panel.GetHandle(),
                                   0, 0, 0)
        elif LINUX:
            (x, y) = (0, 0)
            (width, height) = self.browser_panel.GetSize().Get()
            self.browser.SetBounds(x, y, width, height)
        self.browser.NotifyMoveOrResizeStarted()

    def OnClose(self, event):
        print("[wxpython.py] OnClose called")
        global instance
        result = instance.unload()

        if result == False:
            # If user cancels, veto the event
            print("[wxpython.py] Veto event")
            event.Veto()

            if not self.browser:
                print("Browser is gone (trying to reinitialize)")
                self.create()
            return
        
        if not self.browser:
            # May already be closing, may be called multiple times on Mac
            return

        if MAC:
            # On Mac things work differently, other steps are required
            self.browser.CloseBrowser()
            self.clear_browser_references()
            self.Destroy()
            global g_count_windows
            g_count_windows -= 1
            if g_count_windows == 0:
                cef.Shutdown()
                wx.GetApp().ExitMainLoop()
                # Call _exit otherwise app exits with code 255 (Issue #162).
                # noinspection PyProtectedMember
                os._exit(0)
        else:
            # Calling browser.CloseBrowser() and/or self.Destroy()
            # in OnClose may cause app crash on some paltforms in
            # some use cases, details in Issue #107.
            self.browser.ParentWindowWillClose()
            event.Skip()
            self.clear_browser_references()

        instance.server.close()
        shutil.rmtree(self.tempdir)

    def clear_browser_references(self):
        # Clear browser references that you keep anywhere in your
        # code. All references must be cleared for CEF to shutdown cleanly.
        self.browser = None

class Wrapp(wx.App):
    def __init__(self, redirect):
        self.timer = None
        self.timer_id = 1
        self.is_initialized = False
        super(Wrapp, self).__init__(redirect=redirect)

    def OnPreInit(self):
        super(Wrapp, self).OnPreInit()
        # On Mac with wxPython 4.0 the OnInit() event never gets
        # called. Doing wx window creation in OnPreInit() seems to
        # resolve the problem (Issue #350).
        if MAC and wx.version().startswith("4."):
            print("[wxpython.py] OnPreInit: initialize here"
                  " (wxPython 4.0 fix)")
            self.initialize()

    def OnInit(self):
        self.initialize()
        return True

    def initialize(self):
        if self.is_initialized:
            return
        self.is_initialized = True

        global filenameInput

        self.create_timer()
        frame = mainFrame(filenameInput)
        self.SetTopWindow(frame)
        frame.Show()

    def create_timer(self):
        # See also "Making a render loop":
        # http://wiki.wxwidgets.org/Making_a_render_loop
        # Another way would be to use EVT_IDLE in MainFrame.
        self.timer = wx.Timer(self, self.timer_id)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(10)  # 10ms timer

    def on_timer(self, _):
        cef.MessageLoopWork()

    def OnExit(self):
        self.timer.Stop()
        return 0

# Main ------------------------------------------------------------------------#

if __name__ == '__main__':    
    usage = "Usage: SHTS program.shts [--allow-network-access] \
[--deny-network-access] [--disable-save-warning] [--save-before-creating] \
[--open-DevTools]"
    
    show_info = False
    script_location = os.path.dirname(os.path.abspath(sys.argv[0]))
    shts_file = os.path.join(script_location, filenameInput)
    if len(sys.argv) > 1:
        shts_file = sys.argv[1]
        _, ext = os.path.splitext(sys.argv[1])
        if ext.lower() != ".shts" and ext.lower() != ".shtml":
            show_info = True

    if len(sys.argv) > 2:
        for argument in sys.argv:
            if argument == "--save-before-creating":
                save_before = True
            if argument == "--disable-save-warning":
                disable_save_warning = True
            if argument == "--allow-network-access":
                allow_network_access = [True,True]
            if argument == "--deny-network-access":
                allow_network_access = [True,False]
            if argument == "--open-DevTools":
                open_DevTools = True

    if show_info:
        print(usage)
        
    filenameInput = os.path.abspath(shts_file)
    os.chdir(script_location)

    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    if hasattr(sys, '_MEIPASS'):
        # settings when packaged
        settings = {'locales_dir_path': os.path.join(sys._MEIPASS, 'locales'),
                    'resources_dir_path': sys._MEIPASS,
                    'browser_subprocess_path':
                        os.path.join(sys._MEIPASS, 'subprocess.exe'),
                    'log_file': os.path.join(sys._MEIPASS, 'debug.log')}
    else:
        # settings when unpackaged
        settings = {}
    if MAC:
        # Issue #442 requires enabling message pump on Mac
        # and calling message loop work in a timer both at
        # the same time. This is an incorrect approach
        # and only a temporary fix.
        settings["external_message_pump"] = True
    if WINDOWS:
        pass
        # noinspection PyUnresolvedReferences, PyArgumentList
        cef.DpiAware.EnableHighDpiSupport()
    cef.Initialize(settings=settings, switches={'disable-gpu': ""})
    app = Wrapp(False)
    app.MainLoop()
    del app  # Must destroy before calling Shutdown
    if not MAC:
        # On Mac shutdown is called in OnClose
        cef.Shutdown()
