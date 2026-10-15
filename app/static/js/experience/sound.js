// ============================================================
// SMARTCAR AI — HIGH-TECH SYNTHETIC SOUND ENGINE (WEB AUDIO API)
// sound.js — Pure synthetic audio, zero external files required
// ============================================================

class SmartCarSoundEngine {
    constructor() {
        this.ctx = null;
        this.muted = localStorage.getItem("smartcar-sound-muted") === "true";
        this.initialized = false;
    }

    init() {
        if (this.initialized && this.ctx) return;
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
                this.initialized = true;
            }
        } catch (e) {
            console.warn("SmartCar AudioContext init failed:", e);
        }
    }

    ensureContext() {
        if (!this.ctx) {
            this.init();
        }
        if (this.ctx && this.ctx.state === "suspended") {
            this.ctx.resume().catch(() => {});
        }
    }

    isMuted() {
        return this.muted;
    }

    setMuted(muted) {
        this.muted = !!muted;
        localStorage.setItem("smartcar-sound-muted", this.muted ? "true" : "false");
    }

    toggleMute() {
        this.setMuted(!this.muted);
        return this.muted;
    }

    // Subtle soft hover tick (high-tech feedback)
    playHover() {
        if (this.muted) return;
        this.ensureContext();
        if (!this.ctx) return;

        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            const now = this.ctx.currentTime;

            osc.type = "sine";
            osc.frequency.setValueAtTime(1400, now);
            osc.frequency.exponentialRampToValueAtTime(1800, now + 0.025);

            gain.gain.setValueAtTime(0.015, now);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.03);
        } catch (e) {}
    }

    // Crisp tactile click
    playClick() {
        if (this.muted) return;
        this.ensureContext();
        if (!this.ctx) return;

        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            const now = this.ctx.currentTime;

            osc.type = "triangle";
            osc.frequency.setValueAtTime(800, now);
            osc.frequency.exponentialRampToValueAtTime(320, now + 0.04);

            gain.gain.setValueAtTime(0.04, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.05);
        } catch (e) {}
    }

    // Resonant cybernetic vehicle swap sweep
    playCarSwap() {
        if (this.muted) return;
        this.ensureContext();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;

            // Oscillator 1: Low frequency motor whoosh
            const osc1 = this.ctx.createOscillator();
            const gain1 = this.ctx.createGain();
            osc1.type = "sine";
            osc1.frequency.setValueAtTime(120, now);
            osc1.frequency.exponentialRampToValueAtTime(480, now + 0.16);
            osc1.frequency.exponentialRampToValueAtTime(220, now + 0.35);

            gain1.gain.setValueAtTime(0.001, now);
            gain1.gain.linearRampToValueAtTime(0.05, now + 0.08);
            gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.38);

            osc1.connect(gain1);
            gain1.connect(this.ctx.destination);
            osc1.start(now);
            osc1.stop(now + 0.4);

            // Oscillator 2: High shimmer harmonic
            const osc2 = this.ctx.createOscillator();
            const gain2 = this.ctx.createGain();
            osc2.type = "sine";
            osc2.frequency.setValueAtTime(960, now);
            osc2.frequency.exponentialRampToValueAtTime(1920, now + 0.18);

            gain2.gain.setValueAtTime(0.012, now);
            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

            osc2.connect(gain2);
            gain2.connect(this.ctx.destination);
            osc2.start(now);
            osc2.stop(now + 0.25);
        } catch (e) {}
    }

    // High-tech laser holographic scanner pulse
    playScan() {
        if (this.muted) return;
        this.ensureContext();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(600, now);
            osc.frequency.linearRampToValueAtTime(1200, now + 0.2);

            // Filter for warm laser tone
            const filter = this.ctx.createBiquadFilter();
            filter.type = "lowpass";
            filter.frequency.setValueAtTime(1600, now);

            gain.gain.setValueAtTime(0.02, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);

            osc.connect(filter);
            filter.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.3);
        } catch (e) {}
    }

    // Harmonious major-triad chime for price reveal (C - E - G)
    playChime() {
        if (this.muted) return;
        this.ensureContext();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            const freqs = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6

            freqs.forEach((freq, index) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                const start = now + (index * 0.08);

                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, start);

                gain.gain.setValueAtTime(0.035, start);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.65);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(start);
                osc.stop(start + 0.7);
            });
        } catch (e) {}
    }
}

export const SoundEngine = new SmartCarSoundEngine();
