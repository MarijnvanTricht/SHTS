# SHTS
		
Inspired by the idea of having digital paper: one file script, scripted for each specific case, save-able, recreatable, copyable (just like paper)

Download and install latest binary: (PC - terminal)
```
git clone https://gitlab.com/shts/SHTS.git & cd SHTS & install.bat & cd .. & rmdir SHTS
```

Download and install latest binary: (PC - powershell)
```
git clone https://gitlab.com/shts/SHTS.git; cd SHTS; ./install.bat; cd ..; Remove-Item -Path SHTS -Recurse -Force
```

Download and install latest binary: (MAC)
```
...
```

## How?

SHTS is a program that runs .shts and .shtml files. 
These files are run as if it were .shtml files, with the ability to use the extra functions that SHTS provides.

SHTS exposes the SHTS interface to the shts file which contains 4 functions.

#### .save
`SHTS.save(content)`

This functions saves the HTML content provided as argument to the current file that is running. To create a viable application, the developer of the script is still responsible of making this work and making sure that the data that needs to be loaded and saved is inside a HTML tag. It is recommended to use the following code to save the HTML to the current file:
```
window.addEventListener("beforeunload", (event) => { 
    const content = document.documentElement.outerHTML;
	SHTS.save(content);
});
```

Note that `SHTS.save(content)` will reload the browser with the new content.
		
#### .new
`SHTS.new(content)`
Same as save, but for a new file. Depending on the command line argument `--save-before`, this will either open a save dialog and save a new file at that location with the content or will create a temp file and open the save dialog when the application is closed.
#### .startServer
`SHTS.startServer(port, bridge_info)`

This starts a server. bridge_info can be {protocol:'tcp', port:9090} to start a TCP bridge or {protocol:'udp', inport:9090, outport:9091} to start an UDP bridge.

#### .stopServer
`SHTS.stopServer()`.
This functions stops the server. The server is also automatically closed when the script is closed. 

#### file system access?
Maybe in the future file system handles should be able to be saved on a user-level using the localStorage property.

### Program usage
SHTS can be started with a few command arguments to augment the program behaviour. The arguments are:
- --allow-network-access <i>For allowing the server to start.</i>
- --deny-network-access <i>For disabling the message to allow to start the server.</i>
- --disable-save-warning For disabling the message when the user cancels the save dialog.</i>
- --save-before-creating <i>Default the application creates a tempfile when html content is loaded to a new file with SHTS.new(content). With this argument the user is presented with the save dialog when the SHTS.new(content) function is called instead.</i>

For development reasons the argument --open-DevTools is added to open the DevTools of the browser before loading the page.

`SHTS program.shts [--allow-network-access] [--deny-network-access] [--disable-save-warning] [--save-before-creating] [--open-DevTools]`

### The END

#### missing features
- Interfaces that need permissions in the browser do not work as of yet, like AudioCapture, VideoCapture, Geolocation, Midi MidiSysex (midi), Notifications, ClipboardReadWrite  ClipboardSanitizedWrite (clipboard), BackgroundSync, ProtectedMediaIdentifier, Sensors, PaymentHandler, DurableStorage, IdleDetection, WakeLockScreen, WakeLockSystem, PeriodicBackgroundSync, Nfc.
- fullscreen mode

#### want to help out?

Serious about helping out and feel that you can contribute to one of the items listed below, contact me (marijn@shts.io).
- saving file system handles
- updating binaries for PC and or MAC
- updating code to allow for implementing the missing features
- rewriting SHTS using CEFsharp instead of CEFpython
- creating installers (or scripts for the binaries)
- set file association in windows/mac
- correct me on spelling and writing style and use of terms

<b>Please be resolute, to the point and serious</b>, and give me time to respond.

#### special thanks
- cztomczak for cefpython and a good example script that is used as starting point.