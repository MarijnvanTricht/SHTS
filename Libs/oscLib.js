/*  This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License, with the following exception:
You are free to:

Share — copy and redistribute the material in any medium or format

Adapt — remix, transform, and build upon the material

Under the following terms:

Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.

NonCommercial — You may not use the material for commercial purposes, except when included in an art or creative production.

For more details, please visit the Creative Commons website.*/

let websocket = null;

function startOSCServer(
	port = [null, null, null], 
	onMessageFunc = function(event) { __onMessage(event); },
	onErrorFunc = function(error) {},
	onOpenFunc = function() {}, 
	onCloseFunc = function() {}
	) {
		
	let outport = port[0];
	let inport = port[1];
	let websocketport = port[2];
	
	if ((outport === null || outport === undefined) && (inport === null || inport === undefined)) {
		throw new Error("inport and outport cannot both be null");
	}
	
	if (websocketport === null || websocketport === undefined) {
		if (outport === null || outport === undefined) {
			websocketport = inport - 1;
		} else if (inport === null || inport === undefined) {
			websocketport = outport - 1;
		} else {
			websocketport = (outport - 1 === outport || outport - 1 === inport) ? outport - 2 : outport - 1;
		}
	}
	
	SHTS.startServer(websocketport, {protocol:'udp', outport:outport, inport:inport});
	__openWebSocket(websocketport, onMessageFunc, onErrorFunc, onOpenFunc, onCloseFunc);
}

function stopOSCServer() {
	__closeWebSocket();
	SHTS.stopServer();
}

function __openWebSocket(port, onMessageFunc, onErrorFunc, onOpenFunc, onCloseFunc) {
	if (websocket !== null) {
		alert("WebSocket is already connected.");
		return;
	}
	
	websocket = new WebSocket(`ws://localhost:${port}`);
	
	websocket.onopen = function() {
		console.log("Websocket opened");
		onOpenFunc();
	};
	websocket.onmessage = onMessageFunc;
	websocket.onclose = function() { 
		onCloseFunc();
		console.log("Websocket closed");
		websocket = null;
	};
	websocket.onerror = function(error) {
		console.error(`Error: ${error.message}`);
		onErrorFunc(error);
	};
		
}

function __closeWebSocket() {
	if (websocket !== null) {
		websocket.close();
	}
	
}

function __onMessage(event) {
	if (event.data instanceof Blob) {
		// Convert Blob to ArrayBuffer
		let reader = new FileReader();
		reader.onload = function() {
			let arrayBuffer = reader.result;
			__decodeAndLogOSCMessage(arrayBuffer);
		};
		reader.readAsArrayBuffer(event.data);
	} else if (event.data instanceof ArrayBuffer) {
		// Directly process ArrayBuffer
		__decodeAndLogOSCMessage(event.data);
	} else if (typeof event.data === 'string') {
		// Directly process string
		__decodeAndLogOSCMessage(event.data);
	} else {
		console.error('Unsupported message type:', typeof event.data);
	}
};

function __decodeAndLogOSCMessage(data) {
	try {
		const decodedMessage = decodeOSCMessage(data);
		console.log(`Received message: ${JSON.stringify(decodedMessage)}`);
	} catch (err) {
		console.error('Error decoding message:', err);
	}
}

function sendOSCMessage(oscMessage) {
	if (websocket !== null && websocket.readyState === WebSocket.OPEN) {
		websocket.send(oscMessage);
	} else {
		alert("WebSocket is not connected.");
	}
}

function createOSCMessage(address, args) {
	let buffer = new ArrayBuffer(1024); // Allocate more than needed
	let view = new DataView(buffer);

	// Write the address pattern
	let offset = 0;
	for (let i = 0; i < address.length; i++, offset++) {
		view.setUint8(offset, address.charCodeAt(i));
	}
	view.setUint8(offset++, 0); // Null terminator for address

	// Align to a 4-byte boundary
	while (offset & 0x3) {
		view.setUint8(offset++, 0);
	}

	// Write the types
	let typeOffset = offset;
	view.setUint8(offset++, ','.charCodeAt(0)); // Type tag begins with ','
	for (let arg of args) {
		let type = typeof arg;
		if (type === 'number') {
			view.setUint8(offset++, 'f'.charCodeAt(0)); // Float type
		} else {
			throw new Error("Unsupported argument type");
		}
	}
	view.setUint8(offset++, 0); // Null terminator for types

	// Align to a 4-byte boundary
	while (offset & 0x3) {
		view.setUint8(offset++, 0);
	}

	// Write the arguments
	for (let arg of args) {
		if (typeof arg === 'number') {
			view.setFloat32(offset, arg, false); // Write as big-endian float
			offset += 4;
		}
	}

	return buffer.slice(0, offset); // Trim buffer to the actual size used
}

function decodeOSCMessage(input) {
	// Normalize the input to an ArrayBuffer
	if (typeof input === 'string') {
		// Convert string to Uint8Array
		let encoder = new TextEncoder();
		input = encoder.encode(input);
	}

	if (input instanceof ArrayBuffer) {
		// Input is already an ArrayBuffer, no conversion needed
	} else if (input instanceof Uint8Array || ArrayBuffer.isView(input)) {
		// Convert typed array or other array views to ArrayBuffer
		input = input.buffer.slice(input.byteOffset, input.byteOffset + input.byteLength);
	} else {
		throw new TypeError('Input must be an ArrayBuffer, Uint8Array, or a string');
	}

	let view = new DataView(input);
	let offset = 0;

	// Read the address pattern
	let address = '';
	while (view.getUint8(offset) !== 0) {
		address += String.fromCharCode(view.getUint8(offset++));
	}
	offset++; // Skip the null terminator

	// Align to a 4-byte boundary
	while (offset & 0x3) {
		offset++;
	}

	// Read the type tags
	if (view.getUint8(offset++) !== ','.charCodeAt(0)) {
		throw new Error("Type tags must start with ','");
	}

	let types = '';
	while (view.getUint8(offset) !== 0) {
		types += String.fromCharCode(view.getUint8(offset++));
	}
	offset++; // Skip the null terminator

	// Align to a 4-byte boundary
	while (offset & 0x3) {
		offset++;
	}

	// Read the arguments
	let args = [];
	for (let type of types) {
		if (type === 'f') {
			args.push(view.getFloat32(offset, false)); // Read as big-endian float
			offset += 4;
		} else if (type === 'i') {
			args.push(view.getInt32(offset, false)); // Read as big-endian integer
			offset += 4;
		} else {
			throw new Error("Unsupported argument type");
		}
	}

	return { address, args };
}