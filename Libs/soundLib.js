/*  This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License, with the following exception:
You are free to:

Share — copy and redistribute the material in any medium or format

Adapt — remix, transform, and build upon the material

Under the following terms:

Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.

NonCommercial — You may not use the material for commercial purposes, except when included in an art or creative production.

For more details, please visit the Creative Commons website.*/

// extend the player class to create a source
class Player {
	constructor(audioContext) {
		this.audioContext = audioContext;
		this.gainNode = this.audioContext.createGain();
		this.effectChain = [];
		this.gainNode.connect(this.audioContext.destination);
	}
	
	_midiNoteToFrequency(midiNote) {
		return 440 * Math.pow(2, (midiNote - 69) / 12);
	}

	// Method to play a note, should be implemented by subclasses
	play(midiNote, startTime, duration, loop) {
		throw new Error("The play method should be implemented by subclasses.");
	}
	
	stop() {
		throw new Error("The stop method should be implemented by subclasses.");
	}

	setVolume(volume) {
		this.gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
	}

	addEffect(effectNode) {
		if (this.effectChain.length > 0) {
			const lastNode = this.effectChain[this.effectChain.length - 1];
			lastNode.disconnect(); 
			lastNode.connect(effectNode);
		} else {
		  this.gainNode.disconnect();
		  this.gainNode.connect(effectNode);
		}
		effectNode.connect(this.audioContext.destination);
		this.effectChain.push(effectNode);
	}
}

// sample source
class Sample extends Player {
	constructor(audioContext, arrayBuffer) {
		super(audioContext);
		this.audioBuffer = null;
		this.rootPitch = this._textToPitch("C3");
		this.loadAudio(arrayBuffer);
		this.source = null;
	}

	async loadAudio(arrayBuffer) {
		try {
			this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
		} catch (error) {
			console.error("Error loading audio data:", error);
		}
	}
	
	setRootFreq(freq) {
		this.rootPitch = freq;
	}
	
	setRootNote(note) {
		this.rootPitch = this._midiNoteToFrequency(note);
	}

	_textToPitch(note) {
		const noteFrequencies = {
			C: 261.63,
			'C#': 277.18,
			Db: 277.18,
			D: 293.66,
			'D#': 311.13,
			Eb: 311.13,
			E: 329.63,
			F: 349.23,
			'F#': 369.99,
			Gb: 369.99,
			G: 392.0,
			'G#': 415.3,
			Ab: 415.3,
			A: 440.0,
			'A#': 466.16,
			Bb: 466.16,
			B: 493.88,
		};

		const match = note.match(/^([A-Ga-g])([#b]?)(\d)$/);

		if (!match) {
			console.warn(`Invalid note format: ${note}`);
			return 440.0; // Default to A4
		}

		const [, baseNote, accidental, octaveStr] = match;
		const octave = parseInt(octaveStr, 10);
		const noteName = (baseNote + accidental).toUpperCase();
		const baseFrequency = noteFrequencies[noteName];

		if (!baseFrequency) {
			console.warn(`Unknown note: ${note}`);
			return 440.0;
		}

		const frequency = baseFrequency * Math.pow(2, octave - 4);
		return frequency;
	}

	play(midiNote, startTime, duration, loop=false) {
		if (this.audioBuffer) {
			if (!(loop && this.source)) {
				this.source = this.audioContext.createBufferSource();
				this.source.buffer = this.audioBuffer;
				this.source.loop = loop;

				const targetFrequency = this._midiNoteToFrequency(midiNote);
				const playbackRate = targetFrequency / this.rootPitch;
				this.source.playbackRate.setValueAtTime(playbackRate, startTime);

				this.source.onended = (function() {
					this.source = null;
				}).bind(this);
				
				this.source.connect(this.gainNode);
				this.source.start(startTime);
				
				if (!loop) {
					this.source.stop(startTime + this.duration);
				}
			}
		}
	}
	
	stop() {
		if (this.source) {
			this.source.stop();
			this.source = null;
		}
	}
}

// synth source
class Synth extends Player {
	constructor(audioContext, waveType = 'sine', duration = 1) {
		super(audioContext);
		this.waveType = waveType;
		this.duration = duration;
		this.oscillator = null;
	}

	play(midiNote, startTime, duration, loop=false) {
		if (!(loop && this.oscillator)) {
			this.oscillator = this.audioContext.createOscillator();
			this.oscillator.type = this.waveType;
			this.oscillator.loop = loop;
			this.oscillator.frequency.setValueAtTime(this._midiNoteToFrequency(midiNote), startTime); 

			this.oscillator.onended = (function() {
				this.oscillator.stop();
				this.oscillator = null;
			}).bind(this);
					
			this.oscillator.connect(this.gainNode);
			this.oscillator.start(startTime);
			
			if (!loop) {
				this.oscillator.stop(startTime + this.duration);
			}
		} else {
			if (this.oscillator) {
				this.oscillator.frequency.setValueAtTime(this._midiNoteToFrequency(midiNote), startTime); 
			}
		}
	}
	
	stop() {
		if (this.oscillator) {
			this.oscillator.stop();
			this.oscillator = null;
		}
	}
}

// Track (using only 1 source)
// Default lookahead in seconds (200ms)
class Track {
	constructor(source, tempo = 108, timeSignature = [4, 4]) {
		this.audioContext = source.audioContext;
		this.source = source;
		this.tempo = tempo;
		this.timeSignature = timeSignature;
		this.position = 0;
		this.time = this.audioContext.currentTime;
		this.lookaheadTime = 0.2; 
		this.loopTime = 0;
		this.notes = []; 
		this.loopBars = 0;
		this.isPlaying = false;
		this.intervalId = null;
	}

	// Add a note to the track at a specific grid position with a duration
	add(midiNote = 69, gridPosition = 0, duration = 1) {
		this.notes.push({ midiNote, gridPosition, duration });
	}

	// Remove a note from the track at a specific grid position
	remove(midiNote = 69, gridPosition = 0) {
		this.notes = this.notes.filter(
			(note) => !(note.midiNote === midiNote && note.gridPosition === gridPosition)
		);
	}
  
	addEffect(effectNode) {
		source.addEffect(effectNode);
	}
  
	setVolume(volume) {
		source.setVolume(volume);
	}
  
	syncTime(time) {
		this.time = time;
	}

	// lookahead in ms
	lookahead(lookahead = 500) {
		this.lookaheadTime = lookahead / 1000;
	}

	loop(bars = 4) {
		this.loopBars = bars;
		this.startLoopPosition = this.position;
	}

	// Play the track, scheduling notes in advance
	play() {
		if (this.isPlaying) return;
		this.isPlaying = true;
		this.time = this.audioContext.currentTime;

		let playedNotes = [];

		const loopTime = (obj) => {
			const beatsPerBar = obj.timeSignature[0];
			const beatDuration = 60 / obj.tempo;
			return obj.loopBars * beatsPerBar * beatDuration;
		}
		
		const positionToTime = (obj, position) => {
			const beatsPerBar = obj.timeSignature[0];
			const beatDuration = 60 / obj.tempo;
			const barDuration = beatsPerBar * beatDuration;
			const positionTime = (position / (obj.timeSignature[1] * 4)) * barDuration;
			return obj.time + positionTime;
		}

		const positionsToDuration = (obj, positions) => {
			const beatsPerBar = obj.timeSignature[0];
			const beatValue = obj.timeSignature[1];
			const beatDuration = 60 / obj.tempo;
			return (positions / beatValue) * beatDuration;
		}

		this.intervalId = setInterval(() => {
			// Schedule notes with a regular interval
			while (this.notes.length > 0) {
				const note = this.notes.shift();
				const noteTime = positionToTime(this, note.gridPosition);
				const noteDuration = positionsToDuration(this, note.duration);

				if (noteTime <= this.audioContext.currentTime + this.lookaheadTime) {
					this.source.play(note.midiNote, noteTime, noteDuration);
					playedNotes.push(note); // Move note to playedNotes
				} else {
					this.notes.unshift(note); // Re-add the note to be played later
					break;
				}
			}

			// Handle looping
			const looptime = loopTime(this);
			if (looptime > 0 && this.audioContext.currentTime + this.lookaheadTime  >= this.time + looptime) {
				this.time += looptime;
				this.position = this.startLoopPosition;

				// Restore notes for the new loop
				this.notes = this.notes.concat(playedNotes);
				playedNotes = []; 
			}
		}, 25);
	}

	pause() {
		this.isPlaying = false;
		if (this.intervalId !== null) {
			clearInterval(this.intervalId);
			this.intervalId = null;
		}
	}

	stop() {
		this.pause();
		this.position = 0;
		this.time = this.audioContext.currentTime;
	}
}

// Track list for syncing tracks
class TrackList {
	constructor() {
		this.tracks = [];
		this.isPlaying = false;
		this.currentTime = 0;
		this.intervalId = null;
	}

	addTrack(track) {
		this.tracks.push(track);
	}

	removeTrack(track) {
		this.tracks = this.tracks.filter((t) => t !== track);
	}

	syncTime(time) {
		this.currentTime = time;
		this.tracks.forEach((track) => track.syncTime(time));
	}

	loop(bars = 4) {
		this.tracks.forEach((track) => track.loop(bars));
	}

	play() {
		if (this.isPlaying) return;
		this.isPlaying = true;
	
		const referenceTime = this.tracks[0].audioContext.currentTime;
		this.tracks.forEach((track) => track.play());
		this.syncTime(referenceTime);
	}

	pause() {
		this.isPlaying = false;
		if (this.intervalId !== null) {
			clearInterval(this.intervalId);
			this.intervalId = null;
		}
		this.tracks.forEach((track) => track.pause());
	}

	stop() {
		this.pause();
		this.currentTime = 0;
		this.tracks.forEach((track) => track.stop());
	}
}

async function fetchFromUrl(url) {
	try {
		const response = await fetch(url, {
			method: 'GET',
		});

		if (!response.ok) {
			throw new Error(`HTTP error! Status: ${response.status}`);
		}

		const arrayBuffer = await response.arrayBuffer();
		return arrayBuffer;
	} catch (error) {
		console.error('Error fetching and returning array buffer:', error);
	}
}