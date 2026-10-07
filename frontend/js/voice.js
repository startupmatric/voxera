window.Voice = (() => {
  let mediaRecorder = null;
  let mediaStream = null;
  let chunks = [];
  let onChunk = null;
  let onEnd = null;
  let muted = false;

  async function start(opts = {}) {
    onChunk = opts.onChunk || (() => {});
    onEnd = opts.onEnd || (() => {});

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chunks = [];

    const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    mediaRecorder = new MediaRecorder(mediaStream, { mimeType: mime });

    mediaRecorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) {
        chunks.push(ev.data);
        onChunk(ev.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      chunks = [];
      onEnd(blob);
    };

    mediaRecorder.start(200); // emit chunks every 200ms
  }

  function stop() {
    return new Promise((resolve) => {
      if (!mediaRecorder) return resolve();
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        chunks = [];
        resolve(blob);
      };
      try { mediaRecorder.stop(); } catch {}
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
        mediaStream = null;
      }
    });
  }

  function isRecording() {
    return mediaRecorder && mediaRecorder.state === "recording";
  }

  function setMuted(m) {
    muted = !!m;
    if (mediaStream) {
      mediaStream.getAudioTracks().forEach((t) => { t.enabled = !muted; });
    }
  }

  function isMuted() { return muted; }

  return { start, stop, isRecording, setMuted, isMuted };
})();
